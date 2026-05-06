"""Search client abstraction for ResearcherAgent."""

from __future__ import annotations

from typing import Any

from multi_agent_research_lab.core.config import Settings, get_settings
from multi_agent_research_lab.core.errors import LabError
from multi_agent_research_lab.core.schemas import SourceDocument


class SearchConfigError(LabError):
    """Raised when search client configuration is invalid."""


class SearchRecoverableError(LabError):
    """Raised for transient search failures that should not crash workflow."""


class SearchClient:
    """Provider-agnostic search client with Tavily-compatible interface."""

    def __init__(self, settings: Settings | None = None, tavily_client: Any | None = None) -> None:
        self._settings = settings or get_settings()
        self._tavily_client = tavily_client

    def search(self, query: str, max_results: int = 5) -> list[SourceDocument]:
        """Search for documents relevant to a query."""

        self._validate_config()
        client = self._tavily_client or self._build_default_client()

        capped_results = min(max_results, self._settings.tavily_max_results)
        try:
            payload = client.search(
                query=query,
                max_results=capped_results,
                timeout_seconds=self._settings.tavily_timeout_seconds,
            )
        except SearchRecoverableError:
            return []
        except Exception as exc:
            raise SearchRecoverableError("Search provider call failed") from exc

        return self._normalize_results(payload)

    def _validate_config(self) -> None:
        if not self._settings.tavily_api_key:
            raise SearchConfigError("TAVILY_API_KEY is required for SearchClient")

    def _build_default_client(self) -> Any:
        try:
            from tavily import TavilyClient
        except ImportError as exc:
            raise SearchConfigError("tavily-python package is required when tavily_client is not provided") from exc

        return TavilyClient(api_key=self._settings.tavily_api_key)

    @staticmethod
    def _normalize_results(payload: Any) -> list[SourceDocument]:
        if not isinstance(payload, dict):
            return []

        raw_results = payload.get("results")
        if not isinstance(raw_results, list):
            return []

        normalized: list[SourceDocument] = []
        for item in raw_results:
            if not isinstance(item, dict):
                continue

            title = item.get("title")
            snippet = item.get("content")
            if not isinstance(title, str) or not title.strip():
                continue
            if not isinstance(snippet, str) or not snippet.strip():
                continue

            url = item.get("url")
            score = item.get("score")
            metadata = {"score": score} if score is not None else {}

            normalized.append(
                SourceDocument(
                    title=title,
                    url=url if isinstance(url, str) else None,
                    snippet=snippet,
                    metadata=metadata,
                )
            )

        return normalized
