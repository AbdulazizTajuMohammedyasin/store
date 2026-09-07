from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from langchain_core.messages import AIMessage, AIMessageChunk

from chatbot.services.agent import ChatAgent

User = get_user_model()


class ChatAgentInvokeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="dave", password="pass12345"
        )
        self.customer = self.user.customer

    @patch("chatbot.services.agent.get_llm")
    def test_invoke_returns_plain_text_when_no_tool_calls(self, mock_get_llm):
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        mock_llm.bind_tools.return_value = mock_llm
        mock_llm.invoke.return_value = AIMessage(content="Hi there!")

        result = ChatAgent(self.customer).invoke("hello")

        self.assertEqual(result, "Hi there!")
        mock_llm.invoke.assert_called_once()

    @patch("chatbot.services.agent.get_llm")
    def test_invoke_executes_tool_call_then_returns_final_answer(
        self, mock_get_llm
    ):
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        mock_llm.bind_tools.return_value = mock_llm

        tool_call_response = AIMessage(
            content="",
            tool_calls=[{"name": "view_cart", "args": {}, "id": "call_1"}],
        )
        final_response = AIMessage(content="Your cart is empty.")
        mock_llm.invoke.side_effect = [tool_call_response, final_response]

        result = ChatAgent(self.customer).invoke("what's in my cart?")

        self.assertEqual(result, "Your cart is empty.")
        self.assertEqual(mock_llm.invoke.call_count, 2)

    @patch("chatbot.services.agent.get_llm")
    def test_invoke_handles_unknown_tool_name_gracefully(self, mock_get_llm):
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        mock_llm.bind_tools.return_value = mock_llm

        bad_call_response = AIMessage(
            content="",
            tool_calls=[
                {"name": "not_a_real_tool", "args": {}, "id": "call_1"}
            ],
        )
        final_response = AIMessage(content="ok")
        mock_llm.invoke.side_effect = [bad_call_response, final_response]

        result = ChatAgent(self.customer).invoke("do something weird")

        self.assertEqual(result, "ok")

    @patch("chatbot.services.agent.get_llm")
    def test_invoke_stops_after_max_iterations(self, mock_get_llm):
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        mock_llm.bind_tools.return_value = mock_llm

        looping_response = AIMessage(
            content="",
            tool_calls=[{"name": "view_cart", "args": {}, "id": "call_x"}],
        )
        mock_llm.invoke.return_value = looping_response

        result = ChatAgent(self.customer).invoke("loop forever")

        self.assertEqual(mock_llm.invoke.call_count, ChatAgent.MAX_TOOL_ITERATIONS)
        self.assertIn("couldn't complete", result)

    @patch("chatbot.services.agent.get_llm")
    def test_invoke_falls_back_gracefully_when_llm_raises(self, mock_get_llm):
        """
        A failure talking to the model (e.g. a rate limit error) must
        never propagate as an exception -- the caller always gets a
        string back, so the already-persisted user message never ends
        up with no reply.
        """
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        mock_llm.bind_tools.return_value = mock_llm
        mock_llm.invoke.side_effect = RuntimeError("simulated API failure")

        result = ChatAgent(self.customer).invoke("hello")

        self.assertIsInstance(result, str)
        self.assertIn("couldn't complete", result)

    @patch("chatbot.services.agent.get_llm")
    def test_recommended_products_tool_has_no_customer_argument(
        self, mock_get_llm
    ):
        """
        The customer-scoped tool must never expose a customer/customer_id
        argument the LLM could control.
        """
        mock_get_llm.return_value.bind_tools.return_value = MagicMock()

        agent = ChatAgent(self.customer)

        for tool_name in ["recommended_products", "view_cart", "list_my_orders"]:
            with self.subTest(tool=tool_name):
                self.assertEqual(agent.tools_by_name[tool_name].args, {})


class ChatAgentExtractTextTests(TestCase):
    def test_extract_text_handles_plain_string(self):
        self.assertEqual(ChatAgent._extract_text("hello"), "hello")

    def test_extract_text_handles_content_block_list(self):
        content = [
            {"type": "text", "text": "hello", "extras": {"signature": "x"}}
        ]
        self.assertEqual(ChatAgent._extract_text(content), "hello")

    def test_extract_text_handles_empty_list(self):
        self.assertEqual(ChatAgent._extract_text([]), "")


class ChatAgentInvokeStreamTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="erin", password="pass12345"
        )
        self.customer = self.user.customer

    @patch("chatbot.services.agent.get_llm")
    def test_invoke_stream_yields_text_chunks(self, mock_get_llm):
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        mock_llm.bind_tools.return_value = mock_llm

        chunks = [
            AIMessageChunk(content=[{"type": "text", "text": "Hel", "index": 0}]),
            AIMessageChunk(content=[{"type": "text", "text": "lo!", "index": 0}]),
        ]
        mock_llm.stream.return_value = iter(chunks)

        result = list(ChatAgent(self.customer).invoke_stream("hi"))

        self.assertEqual("".join(result), "Hello!")

    @patch("chatbot.services.agent.get_llm")
    def test_invoke_stream_falls_back_gracefully_when_llm_raises(
        self, mock_get_llm
    ):
        """
        Streaming counterpart of the invoke() failure test: a failure
        mid-stream must still end the generator normally (yielding a
        fallback message) rather than raising out of it, so the calling
        view still has something to persist as the assistant's reply.
        """
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        mock_llm.bind_tools.return_value = mock_llm
        mock_llm.stream.side_effect = RuntimeError("simulated API failure")

        result = list(ChatAgent(self.customer).invoke_stream("hi"))

        self.assertEqual(len(result), 1)
        self.assertIn("couldn't complete", result[0])

    @patch("chatbot.services.agent.get_llm")
    def test_invoke_stream_executes_tool_call_without_yielding_text(
        self, mock_get_llm
    ):
        mock_llm = MagicMock()
        mock_get_llm.return_value = mock_llm
        mock_llm.bind_tools.return_value = mock_llm

        tool_chunk = AIMessageChunk(
            content=[],
            tool_call_chunks=[
                {"name": "view_cart", "args": "{}", "id": "call_1", "index": 0}
            ],
        )
        final_chunk = AIMessageChunk(
            content=[
                {"type": "text", "text": "Your cart is empty.", "index": 0}
            ]
        )
        mock_llm.stream.side_effect = [iter([tool_chunk]), iter([final_chunk])]

        result = list(ChatAgent(self.customer).invoke_stream("what's in my cart"))

        self.assertEqual("".join(result), "Your cart is empty.")
        self.assertEqual(mock_llm.stream.call_count, 2)
