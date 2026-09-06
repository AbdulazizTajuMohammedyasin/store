from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from .llm import get_llm
from .prompt import SYSTEM_PROMPT
from .tools.product_tool import product_search


class ChatAgent:
    MAX_TOOL_ITERATIONS = 5

    TOOLS = [product_search]

    def __init__(self):
        self.llm = get_llm()
        self.llm_with_tools = self.llm.bind_tools(self.TOOLS)
        self.tools_by_name = {tool.name: tool for tool in self.TOOLS}

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
