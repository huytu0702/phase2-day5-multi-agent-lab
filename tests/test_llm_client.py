from __future__ import annotations

from pydantic import BaseModel

from multi_agent_research_lab.core.config import Settings
from multi_agent_research_lab.services.llm_client import (
    LLMClient,
    LLMConfigError,
    LLMRecoverableError,
)


class FakeChatCompletions:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        item = self._responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class FakeClient:
    def __init__(self, responses):
        self.chat = type("Chat", (), {"completions": FakeChatCompletions(responses)})()


class _Usage:
    def __init__(self, prompt_tokens=10, completion_tokens=20):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens


class _Message:
    def __init__(self, content: str):
        self.content = content


class _Choice:
    def __init__(self, content: str):
        self.message = _Message(content)


class _Response:
    def __init__(self, content: str):
        self.choices = [_Choice(content)]
        self.usage = _Usage()


class StructuredOut(BaseModel):
    answer: str
    confidence: float


def test_default_model_is_gpt_5_4_mini() -> None:
    settings = Settings(OPENAI_API_KEY="x")
    assert settings.openai_model == "gpt-5.4-mini"


def test_missing_api_key_fails_fast() -> None:
    settings = Settings(OPENAI_API_KEY=None)
    client = LLMClient(settings=settings, sdk_client=object())

    try:
        client.complete("sys", "user")
        assert False, "Expected LLMConfigError"
    except LLMConfigError as exc:
        assert "OPENAI_API_KEY" in str(exc)


def test_retries_transient_failure_then_succeeds() -> None:
    fake = FakeClient([LLMRecoverableError("transient"), _Response("hello")])
    settings = Settings(OPENAI_API_KEY="x", OPENAI_MAX_RETRIES=2)
    client = LLMClient(settings=settings, sdk_client=fake)

    result = client.complete("sys", "user")

    assert result.content == "hello"
    assert fake.chat.completions.calls == 2


def test_complete_structured_parses_json_payload() -> None:
    fake = FakeClient([_Response('{"answer":"ok","confidence":0.8}')])
    settings = Settings(OPENAI_API_KEY="x")
    client = LLMClient(settings=settings, sdk_client=fake)

    result = client.complete_structured("sys", "user", StructuredOut)

    assert isinstance(result, StructuredOut)
    assert result.answer == "ok"
