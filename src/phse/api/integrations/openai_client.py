"""
OpenAI API Client Integration.
Follows the same abstract interface as OpenRouter and Gemini clients.
Reads credentials from .env, handles retries, rate limits, failures, logs errors.
"""
import os
import logging
from .base_client import BaseAPIClient

logger = logging.getLogger(__name__)


class OpenAIClient(BaseAPIClient):
    """OpenAI-compatible API client for text completions."""

    def __init__(self):
        api_key = os.environ.get("OPENAI_API_KEY", "")
        super().__init__(
            base_url="https://api.openai.com/v1",
            api_key=api_key,
            max_retries=3,
            timeout=30
        )
        if not api_key:
            logger.info("OPENAI_API_KEY not configured. OpenAI client inactive.")

    async def generate_completion(self, messages: list, model: str = "gpt-4o-mini", temperature: float = 0.3) -> str | None:
        if not self.api_key:
            return None
        try:
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": 1024
            }
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            data = await self._post("/chat/completions", json_data=payload, headers=headers)
            if data and "choices" in data:
                return data["choices"][0]["message"]["content"]
            return None
        except Exception as e:
            logger.error(f"OpenAI completion error: {e}")
            return None
