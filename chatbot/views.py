from django.http import StreamingHttpResponse
from langchain_core.messages import AIMessage, HumanMessage
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from products.models import Customer

from .models import Conversation, Message
from .serializers import ChatMessageSerializer, MessageSerializer
from .services.agent import ChatAgent


class BaseChatView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_customer(self, request):
        return Customer.objects.get(user=request.user)

    def _get_conversation(self, request):
        customer = self._get_customer(request)
        return Conversation.objects.filter(customer=customer).first()

    def _build_history(self, conversation):
        return [
            HumanMessage(content=message.content)
            if message.role == Message.Role.USER
            else AIMessage(content=message.content)
            for message in conversation.messages.all()
        ]


class ChatView(BaseChatView):

    def get(self, request):
        conversation = self._get_conversation(request)
        messages = conversation.messages.all() if conversation else []

        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ChatMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        text = serializer.validated_data["message"]

        customer = self._get_customer(request)
        conversation, _ = Conversation.objects.get_or_create(customer=customer)

        history = self._build_history(conversation)

        Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content=text,
        )

        reply = ChatAgent(customer).invoke(text, history=history)

        Message.objects.create(
            conversation=conversation,
            role=Message.Role.ASSISTANT,
            content=reply,
        )

        return Response(
            {
                "message": reply,
            },
            status=status.HTTP_200_OK,
        )


class ChatStreamView(BaseChatView):

    def post(self, request):
        serializer = ChatMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        text = serializer.validated_data["message"]

        customer = self._get_customer(request)
        conversation, _ = Conversation.objects.get_or_create(customer=customer)

        history = self._build_history(conversation)

        Message.objects.create(
            conversation=conversation,
            role=Message.Role.USER,
            content=text,
        )

        agent = ChatAgent(customer)

        def stream():
            full_text = ""

            for chunk in agent.invoke_stream(text, history=history):
                full_text += chunk
                yield chunk

            Message.objects.create(
                conversation=conversation,
                role=Message.Role.ASSISTANT,
                content=full_text,
            )

        return StreamingHttpResponse(stream(), content_type="text/plain; charset=utf-8")
