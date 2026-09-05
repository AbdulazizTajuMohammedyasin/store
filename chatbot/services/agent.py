from langchain_core.messages import HumanMessage, ToolMessage

from .llm import get_llm
from .tools.product_tool import product_search


class ChatAgent:
    MAX_TOOL_ITERATIONS = 5

    TOOLS = [product_search]

    def __init__(self):
        self.llm = get_llm()
        self.llm_with_tools = self.llm.bind_tools(self.TOOLS)
        self.tools_by_name = {tool.name: tool for tool in self.TOOLS}

    def invoke(self, message: str):
        messages = [HumanMessage(content=message)]

        for _ in range(self.MAX_TOOL_ITERATIONS):
            response = self.llm_with_tools.invoke(messages)
            messages.append(response)

            if not response.tool_calls:
                return response.content

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
