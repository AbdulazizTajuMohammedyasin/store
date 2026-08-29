from langchain_core.messages import HumanMessage

from .llm import get_llm


class ChatAgent:
    def __init__(self):
        self.llm = get_llm()

    def invoke(self, message: str):
        response = self.llm.invoke(
            [
                HumanMessage(content=message),
            ]
        )

        return response.content