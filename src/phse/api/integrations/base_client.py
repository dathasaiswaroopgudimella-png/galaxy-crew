import os
import logging
import httpx
import asyncio
from typing import Dict, Any, Optional

logger = logging.getLogger("phse.api.integrations")

class BaseClient:
    """
    Abstract base class for API integration clients.
    Handles network failures, rate limiting, and exponential backoff.
    """
    def __init__(self, api_key_env_var: str, base_url: str):
        self.api_key = os.getenv(api_key_env_var)
        self.base_url = base_url
        if not self.api_key:
            logger.warning(f"API key environment variable '{api_key_env_var}' is not configured.")

    async def _post_request(
        self,
        endpoint: str,
        payload: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        max_retries: int = 3,
        initial_backoff: float = 1.0
    ) -> Optional[Dict[str, Any]]:
        """
        Executes a POST request with exponential backoff and rate limit handling.
        """
        if not self.api_key:
            logger.error(f"Cannot complete request to {self.base_url}/{endpoint}: Missing API Key.")
            return None

        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        req_headers = {
            "Content-Type": "application/json"
        }
        if headers:
            req_headers.update(headers)

        backoff = initial_backoff
        async with httpx.AsyncClient(timeout=30.0) as client:
            for attempt in range(max_retries):
                try:
                    logger.debug(f"POST {url} - Attempt {attempt + 1}")
                    response = await client.post(url, json=payload, headers=req_headers)
                    
                    if response.status_code == 200:
                        return response.json()
                    
                    # Handle rate limit (429) or temporary server errors (500, 502, 503, 504)
                    if response.status_code in [429, 500, 502, 503, 504]:
                        logger.warning(f"Request failed with status {response.status_code}. Retrying in {backoff}s...")
                        await asyncio.sleep(backoff)
                        backoff *= 2.0
                        continue
                    
                    logger.error(f"HTTP error {response.status_code}: {response.text}")
                    return None
                    
                except httpx.NetworkError as ne:
                    logger.warning(f"Network error on attempt {attempt + 1}: {ne}. Retrying...")
                    await asyncio.sleep(backoff)
                    backoff *= 2.0
                except Exception as e:
                    logger.error(f"Unexpected request error: {e}")
                    return None
                    
            logger.error(f"Failed to fetch response after {max_retries} attempts.")
            return None
