from langchain.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from .llm import get_llm
from .prompt import SYSTEM_PROMPT
from .tools.product_tool import product_details, product_search
from .tools.recommendations import get_recommended_products_for_customer, similar_products
from .tools.reviews import product_reviews


class ChatAgent:
    MAX_TOOL_ITERATIONS = 5

    def __init__(self, customer):
        self.customer = customer
        self.llm = get_llm()

        self.tools = [
            product_search,
            product_details,
            product_reviews,
            similar_products,
            self._recommended_products_tool(),
        ]

        self.llm_with_tools = self.llm.bind_tools(self.tools)
        self.tools_by_name = {t.name: t for t in self.tools}

    def _recommended_products_tool(self):
        customer_id = self.customer.id

        @tool
        def recommended_products():
            """
            Get personalized product recommendations for the current
            customer, based on their past orders.
            """
            return get_recommended_products_for_customer(customer_id)

        return recommended_products

    def invoke(self, message: str, history: list | None = None):
        messages = (
            [SystemMessage(content=SYSTEM_PROMPT)]
            + list(history or [])
            + [HumanMessage(content=message)]
        )

        for _ in range(self.MAX_TOOL_ITERATIONS):
            response = self.llm_with_tools.invoke(messages)
            messages.append(response)

            if not response.tool_calls:
                return self._extract_text(response.content)

            for tool_call in response.tool_calls:
                tool = self.tools_by_name.get(tool_call["name"])

                if tool is None:
                    result = f"Unknown tool: {tool_call['name']}"
                else:
                    result = tool.invoke(tool_call["args"])

                messages.append(
                    ToolMessage(
                        content=str(result),
                        tool_call_id=tool_call["id"],
                    )
                )

        return (
            "I couldn't complete that request right now. "
            "Please try rephrasing."
        )

    @staticmethod
    def _extract_text(content) -> str:
        """
        Normalize a LangChain message's `.content` into a plain string.

        Newer langchain-google-genai versions return `.content` as a list
        of content blocks (e.g. `{"type": "text", "text": "...", "extras": {...}}`)
        instead of a plain string, so this keeps the string contract
        expected by the rest of the app (persisted messages, API response).
        """
        if isinstance(content, str):
            return content

        if isinstance(content, list):
            parts = []

            for block in content:
                if isinstance(block, str):
                    parts.append(block)
                elif isinstance(block, dict) and block.get("type") == "text":
                    parts.append(block.get("text", ""))

            return "".join(parts)

        return str(content)
