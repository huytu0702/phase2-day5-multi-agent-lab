"""LLM client abstraction.

Production note: agents should depend on this interface instead of importing an SDK directly.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from time import sleep
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError as PydanticValidationError

from multi_agent_research_lab.core.config import Settings, get_settings
from multi_agent_research_lab.core.errors import LabError


class LLMConfigError(LabError):
    """Raised when LLM client configuration is invalid."""


class LLMRecoverableError(LabError):
    """Raised for transient model/API failures that can be retried."""


@dataclass(frozen=True)
class LLMResponse:
    content: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None


StructuredModelT = TypeVar("StructuredModelT", bound=BaseModel)


class LLMClient:
    """Provider-agnostic LLM client."""

    def __init__(self, settings: Settings | None = None, sdk_client: Any | None = None) -> None:
        self._settings = settings or get_settings()
        self._sdk_client = sdk_client

    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Return a model completion with retries for recoverable failures."""

        self._validate_config()
        client = self._sdk_client or self._build_default_client()

        max_attempts = self._settings.openai_max_retries + 1
        for attempt in range(max_attempts):
            try:
                response = client.chat.completions.create(
                    model=self._settings.openai_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    timeout=self._settings.openai_timeout_seconds,
                )
                content = self._extract_content(response)
                prompt_tokens = getattr(getattr(response, "usage", None), "prompt_tokens", None)
                completion_tokens = getattr(getattr(response, "usage", None), "completion_tokens", None)
                return LLMResponse(
                    content=content,
                    input_tokens=prompt_tokens,
                    output_tokens=completion_tokens,
                    cost_usd=None,
                )
            except LLMRecoverableError:
                if attempt >= max_attempts - 1:
                    raise
                sleep(0.05)
            except Exception as exc:
                if attempt >= max_attempts - 1:
                    raise LLMRecoverableError("Transient LLM provider error after retries") from exc
                sleep(0.05)

        raise LLMRecoverableError("LLM call failed after retries")

    def complete_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: type[StructuredModelT],
    ) -> StructuredModelT:
        """Request a completion and parse the content into the given Pydantic model."""

        raw = self.complete(system_prompt, user_prompt)
        payload_text = self._extract_json_payload(raw.content)
        try:
            payload = json.loads(payload_text)
            return response_model.model_validate(payload)
        except (json.JSONDecodeError, PydanticValidationError) as exc:
            raise LLMRecoverableError("Structured LLM output is invalid") from exc

    def _validate_config(self) -> None:
        if not self._settings.openai_api_key:
            raise LLMConfigError("OPENAI_API_KEY is required for LLMClient")

    def _build_default_client(self) -> Any:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise LLMConfigError("openai package is required when sdk_client is not provided") from exc
        return OpenAI(api_key=self._settings.openai_api_key, base_url=self._settings.openai_base_url)

    @staticmethod
    def _extract_json_payload(content: str) -> str:
        text = content.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)

        if text.startswith("{") and text.endswith("}"):
            return text

        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return text[start : end + 1]
        return text

    @staticmethod
    def _extract_content(response: Any) -> str:
        choices = getattr(response, "choices", None)
        if not choices:
            raise LLMRecoverableError("LLM response has no choices")

        first_choice = choices[0]
        message = getattr(first_choice, "message", None)
        content = getattr(message, "content", None)
        if not isinstance(content, str) or not content.strip():
            raise LLMRecoverableError("LLM response content is empty")
        return content
