from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import ChatMessageSerializer


class ChatView(APIView):
    def post(self, request):
        serializer = ChatMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        message = serializer.validated_data["message"]

        return Response(
            {
                "message": f"You said: {message}",
            },
            status=status.HTTP_200_OK,
        )