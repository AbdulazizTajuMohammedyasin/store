from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from chatbot.models import Conversation, Message

User = get_user_model()


class ChatEndpointsRequireAuthTests(APITestCase):
    def test_post_chat_requires_authentication(self):
        response = self.client.post("/chat/", {"message": "hi"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_chat_requires_authentication(self):
        response = self.client.get("/chat/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_post_chat_stream_requires_authentication(self):
        response = self.client.post(
            "/chat/stream/", {"message": "hi"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ChatViewConversationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="alice", password="pass12345"
        )
        self.customer = self.user.customer
        self.client.force_authenticate(user=self.user)

    def test_get_with_no_conversation_returns_empty_list(self):
        response = self.client.get("/chat/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    @patch("chatbot.views.ChatAgent")
    def test_post_creates_conversation_and_persists_both_messages(self, MockAgent):
        MockAgent.return_value.invoke.return_value = "Hello! How can I help?"

        response = self.client.post(
            "/chat/", {"message": "hi there"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Hello! How can I help?")

        conversation = Conversation.objects.get(customer=self.customer)
        messages = list(conversation.messages.all())

        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0].role, Message.Role.USER)
        self.assertEqual(messages[0].content, "hi there")
        self.assertEqual(messages[1].role, Message.Role.ASSISTANT)
        self.assertEqual(messages[1].content, "Hello! How can I help?")

    @patch("chatbot.views.ChatAgent")
    def test_second_message_reuses_conversation_and_passes_history(
        self, MockAgent
    ):
        MockAgent.return_value.invoke.return_value = "first reply"
        self.client.post("/chat/", {"message": "first"}, format="json")

        MockAgent.return_value.invoke.return_value = "second reply"
        self.client.post("/chat/", {"message": "second"}, format="json")

        self.assertEqual(
            Conversation.objects.filter(customer=self.customer).count(), 1
        )
        conversation = Conversation.objects.get(customer=self.customer)
        self.assertEqual(conversation.messages.count(), 4)

        _, kwargs = MockAgent.return_value.invoke.call_args_list[1]
        self.assertEqual(len(kwargs["history"]), 2)

    @patch("chatbot.views.ChatAgent")
    def test_get_returns_persisted_history_in_order(self, MockAgent):
        MockAgent.return_value.invoke.return_value = "reply"
        self.client.post("/chat/", {"message": "hi"}, format="json")

        response = self.client.get("/chat/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]["role"], "user")
        self.assertEqual(response.data[1]["role"], "assistant")

    @patch("chatbot.views.ChatAgent")
    def test_conversation_is_isolated_per_customer(self, MockAgent):
        MockAgent.return_value.invoke.return_value = "reply for alice"
        self.client.post("/chat/", {"message": "alice message"}, format="json")

        other_user = User.objects.create_user(
            username="bob", password="pass12345"
        )
        self.client.force_authenticate(user=other_user)

        response = self.client.get("/chat/")
        self.assertEqual(response.data, [])


class ChatStreamViewTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="carol", password="pass12345"
        )
        self.customer = self.user.customer
        self.client.force_authenticate(user=self.user)

    @patch("chatbot.views.ChatAgent")
    def test_stream_assembles_and_persists_full_message(self, MockAgent):
        MockAgent.return_value.invoke_stream.return_value = iter(
            ["Hel", "lo", "!"]
        )

        response = self.client.post(
            "/chat/stream/", {"message": "hi"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = b"".join(response.streaming_content).decode()
        self.assertEqual(body, "Hello!")

        conversation = Conversation.objects.get(customer=self.customer)
        messages = list(conversation.messages.all())

        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0].role, Message.Role.USER)
        self.assertEqual(messages[0].content, "hi")
        self.assertEqual(messages[1].role, Message.Role.ASSISTANT)
        self.assertEqual(messages[1].content, "Hello!")
