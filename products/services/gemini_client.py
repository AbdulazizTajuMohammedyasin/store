from google import genai
from django.conf import settings


class GeminiServiceError(Exception):
    pass


class GeminiClient:

    def __init__(self):
        self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self._model = "gemini-3.5-flash-lite"

    def summarize(self, prompt: str) -> str:
        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=prompt,
            )
            text = response.text.strip()

            if not text:
                raise GeminiServiceError("Gemini returned an empty response")

            return text

        except GeminiServiceError:
            raise
        except Exception as e:
            raise GeminiServiceError(
                f"Gemini API call failed: {e}"
            )