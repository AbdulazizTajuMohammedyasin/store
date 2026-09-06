from django.conf import settings
from google import genai

EMBEDDING_MODEL = "gemini-embedding-001"


def embed_text(text: str) -> list[float]:
    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
    )

    return list(response.embeddings[0].values)
