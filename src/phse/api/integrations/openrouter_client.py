import os
import logging
from typing import Dict, Any, Optional, List
from phse.api.integrations.base_client import BaseClient

logger = logging.getLogger("phse.api.integrations")

class OpenRouterClient(BaseClient):
    """
    OpenRouter API Client.
    Serves as the primary assistant gateway for natural-language Q&A and reports.
    """
    def __init__(self):
        # Fallback to OPENAI_API_KEY if OPENROUTER_API_KEY is not defined
        key_var = "OPENROUTER_API_KEY" if os.getenv("OPENROUTER_API_KEY") else "OPENAI_API_KEY"
        super().__init__(api_key_env_var=key_var, base_url="https://openrouter.ai/api/v1")
        self.default_model = os.getenv("PHSE_OPENROUTER_MODEL", "google/gemini-2.5-pro")

    async def generate_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1500
    ) -> Optional[str]:
        """
        Sends a chat completions request to OpenRouter.
        """
        payload = {
            "model": model or self.default_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/google/gemini-antigravity", # Required by OpenRouter
            "X-Title": "PHSE Lunar Space-Tech Engine"
        }
        
        logger.info(f"Submitting chat request to OpenRouter model: {payload['model']}")
        result = await self._post_request("chat/completions", payload, headers=headers)
        
        if result and "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"]
            
        logger.error("OpenRouter response parsing failed or empty choices returned.")
        return None
