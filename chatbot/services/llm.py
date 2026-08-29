from django.conf import settings
from langchain_google_genai import ChatGoogleGenerativeAI


def get_llm():
    return ChatGoogleGenerativeAI(
        model="gemini-3.5-flash",
        google_api_key=settings.GEMINI_API_KEY,
        temperature=0,
    )