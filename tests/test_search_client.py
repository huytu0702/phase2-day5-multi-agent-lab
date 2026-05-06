from __future__ import annotations

from multi_agent_research_lab.core.config import Settings
from multi_agent_research_lab.services.search_client import (
    SearchClient,
    SearchConfigError,
    SearchRecoverableError,
)


class FakeTavilyClient:
    def __init__(self, payload):
        self.payload = payload

    def search(self, query: str, max_results: int, timeout_seconds: int):
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


def test_tavily_result_maps_to_source_document() -> None:
    payload = {
        "results": [
            {
                "title": "Doc",
                "url": "https://example.com",
                "content": "Snippet body",
                "score": 0.9,
            }
        ]
    }
    client = SearchClient(
        settings=Settings(TAVILY_API_KEY="k"),
        tavily_client=FakeTavilyClient(payload),
    )

    docs = client.search("query", max_results=3)

    assert len(docs) == 1
    assert docs[0].title == "Doc"
    assert docs[0].url == "https://example.com"
    assert docs[0].snippet == "Snippet body"


def test_empty_tavily_result_is_handled_explicitly() -> None:
    client = SearchClient(
        settings=Settings(TAVILY_API_KEY="k"),
        tavily_client=FakeTavilyClient({"results": []}),
    )

    docs = client.search("query")

    assert docs == []


def test_invalid_result_does_not_crash_workflow() -> None:
    payload = {"results": [{"title": "No content"}]}
    client = SearchClient(
        settings=Settings(TAVILY_API_KEY="k"),
        tavily_client=FakeTavilyClient(payload),
    )

    docs = client.search("query")

    assert docs == []


def test_missing_tavily_key_fails_fast() -> None:
    client = SearchClient(settings=Settings(TAVILY_API_KEY=None), tavily_client=FakeTavilyClient({}))

    try:
        client.search("query")
        assert False, "Expected SearchConfigError"
    except SearchConfigError as exc:
        assert "TAVILY_API_KEY" in str(exc)


def test_recoverable_search_error_returns_empty_list() -> None:
    client = SearchClient(
        settings=Settings(TAVILY_API_KEY="k"),
        tavily_client=FakeTavilyClient(SearchRecoverableError("temporary")),
    )

    docs = client.search("query")

    assert docs == []
