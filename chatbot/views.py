from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from products.services.gemini_client import GeminiClient
from products.services.gemini_client import GeminiServiceError

from .serializers import ChatMessageSerializer
from .services.prompt import build_chat_prompt


class ChatView(APIView):

    def post(self, request):
        serializer = ChatMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        message = serializer.validated_data["message"]
        prompt = build_chat_prompt(message)

        try:
            response = GeminiClient().generate(prompt)
            
        except GeminiServiceError:
            return Response(
                {
                    "detail": "Unable to generate a response right now."
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {
                "message": response,
            },
            status=status.HTTP_200_OK,
        )