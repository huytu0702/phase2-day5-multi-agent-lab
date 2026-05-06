"""Researcher agent implementation."""

from __future__ import annotations

from typing import Protocol

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult, SourceDocument
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.search_client import SearchConfigError, SearchRecoverableError


class _SearchClientProtocol(Protocol):
    def search(self, query: str, max_results: int = 5) -> list[SourceDocument]: ...


class ResearcherAgent(BaseAgent):
    """Collects sources and creates concise research notes."""

    name = "researcher"

    def __init__(self, search_client: _SearchClientProtocol | None = None) -> None:
        self._search_client = search_client

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.sources` and `state.research_notes`."""

        sources = self._load_sources(state)
        state.sources = sources

        citation_lines = [
            f"[{index}] {source.title} - {source.url or 'no-url'}"
            for index, source in enumerate(sources, start=1)
        ]
        evidence_lines = [
            f"- [{index}] {source.snippet.strip()}"
            for index, source in enumerate(sources, start=1)
            if source.snippet.strip()
        ]

        state.research_notes = "\n".join(
            [
                "Research Notes",
                f"Query: {state.request.query}",
                "",
                "Key evidence:",
                *(evidence_lines or ["- No evidence snippets available."]),
                "",
                "Citations:",
                *(citation_lines or ["- No citations collected."]),
            ]
        )

        state.agent_results.append(
            AgentResult(
                agent=AgentName.RESEARCHER,
                content=state.research_notes,
                metadata={"source_count": len(sources)},
                success=True,
            )
        )
        return state

    def _load_sources(self, state: ResearchState) -> list[SourceDocument]:
        if self._search_client is None:
            return list(state.sources)
        try:
            return self._search_client.search(state.request.query, max_results=state.request.max_sources)
        except (SearchConfigError, SearchRecoverableError):
            return list(state.sources)
