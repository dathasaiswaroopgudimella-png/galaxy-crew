import os
import logging
import base64
from typing import Dict, Any, Optional, List
from phse.api.integrations.base_client import BaseClient

logger = logging.getLogger("phse.api.integrations")

class GeminiClient(BaseClient):
    """
    Google Gemini Multimodal API Client.
    Handles visual understanding, architectural discussions, and code review support.
    """
    def __init__(self):
        super().__init__(api_key_env_var="GEMINI_API_KEY", base_url="https://generativelanguage.googleapis.com/v1beta")
        self.default_model = os.getenv("PHSE_GEMINI_MODEL", "gemini-2.5-flash")

    async def generate_multimodal_content(
        self,
        prompt: str,
        image_bytes: Optional[bytes] = None,
        image_mime_type: Optional[str] = "image/png",
        model: Optional[str] = None
    ) -> Optional[str]:
        """
        Generates content from Gemini, supporting optional base64 image data.
        """
        target_model = model or self.default_model
        endpoint = f"models/{target_model}:generateContent?key={self.api_key}"
        
        parts = [{"text": prompt}]
        
        if image_bytes:
            encoded_img = base64.b64encode(image_bytes).decode("utf-8")
            parts.append({
                "inlineData": {
                    "mimeType": image_mime_type,
                    "data": encoded_img
                }
            })
            
        payload = {
            "contents": [
                {
                    "parts": parts
                }
            ],
            "generationConfig": {
                "temperature": 0.4,
                "maxOutputTokens": 2048
            }
        }
        
        logger.info(f"Submitting multimodal request to Gemini model: {target_model}")
        result = await self._post_request(endpoint, payload)
        
        if result and "candidates" in result and len(result["candidates"]) > 0:
            candidate = result["candidates"][0]
            if "content" in candidate and "parts" in candidate["content"] and len(candidate["content"]["parts"]) > 0:
                return candidate["content"]["parts"][0]["text"]
                
        logger.error("Gemini response parsing failed or empty candidate content returned.")
        return None
