"""Groq LLM Client implementation (Layer 2).

Provides real Groq completions with JSON mode support, deterministic error handling,
and strict avoidance of fabricated/mock fallbacks.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from groq import (
    APIConnectionError,
    AuthenticationError,
    Groq,
    GroqError,
    RateLimitError,
)

from src.config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Real Groq LLM client using official Groq Python SDK."""

    def __init__(self):
        self.model = settings.GROQ_MODEL
        self._client: Optional[Groq] = None

    def _get_client(self) -> Groq:
        """Lazily initialize and return the Groq client, validating credentials."""
        settings.validate_groq_credentials()
        if self._client is None or self._client.api_key != settings.GROQ_API_KEY:
            self._client = Groq(api_key=settings.GROQ_API_KEY)
        return self._client

    def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Generate real completion from Groq API.
        
        Args:
            prompt: User message prompt.
            system_prompt: Optional system directive.
            json_mode: Whether to enforce valid JSON object formatting.
            temperature: Sampling temperature (default 0.2 for analytical precision).
            max_tokens: Optional token cap for cost control.
            
        Returns:
            The raw text completion content string.
            
        Raises:
            ValueError: If credentials are missing or response is empty.
            RuntimeError: If Groq API request fails.
        """
        client = self._get_client()

        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # Groq JSON mode requires the word 'json' or 'JSON' to appear in the prompt
        effective_prompt = prompt
        if json_mode:
            combined_text = (system_prompt or "") + " " + prompt
            if "json" not in combined_text.lower():
                effective_prompt = f"Respond strictly with valid JSON.\n\n{prompt}"

        messages.append({"role": "user", "content": effective_prompt})

        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            logger.debug(f"Calling Groq API (model={self.model}, json_mode={json_mode})")
            response = client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content

            if not content or not content.strip():
                raise ValueError("Groq returned an empty response.")

            return content.strip()

        except AuthenticationError as e:
            raise RuntimeError(
                f"Groq Authentication Error: Invalid or expired GROQ_API_KEY. Details: {e}"
            ) from e
        except RateLimitError as e:
            raise RuntimeError(
                f"Groq Rate Limit Error: Free-tier limit reached. Details: {e}"
            ) from e
        except APIConnectionError as e:
            raise RuntimeError(
                f"Groq Connection Error: Unable to reach Groq endpoint. Check internet connection. Details: {e}"
            ) from e
        except GroqError as e:
            raise RuntimeError(f"Groq API Error: {e}") from e
        except Exception as e:
            raise RuntimeError(f"Unexpected error during Groq completion: {e}") from e

    def complete_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Execute a Groq completion and parse the output directly into a Python dictionary.
        
        Raises:
            ValueError: If the response is not valid JSON.
            RuntimeError: If Groq API request fails.
        """
        raw_text = self.complete(
            prompt=prompt,
            system_prompt=system_prompt,
            json_mode=True,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        try:
            return json.loads(raw_text)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Failed to parse Groq response as valid JSON: {e}. Raw content: {raw_text[:200]}..."
            ) from e


# Singleton LLM client instance
llm_client = LLMClient()
