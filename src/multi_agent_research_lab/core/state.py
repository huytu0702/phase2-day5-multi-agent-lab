"""Shared state for the multi-agent workflow.

This state is designed to be LangGraph-friendly with explicit copy-on-write helpers.
"""

from typing import Any

from pydantic import BaseModel, Field

from multi_agent_research_lab.core.schemas import (
    AgentResult,
    JudgeScore,
    ResearchQuery,
    RouteDecision,
    SourceDocument,
    TokenUsage,
    TraceEvent,
)


class ResearchState(BaseModel):
    """Single source of truth passed through the workflow."""

    request: ResearchQuery
    iteration: int = 0
    max_iterations: int = 8

    route_history: list[str] = Field(default_factory=list)
    stop_reason: str | None = None

    sources: list[SourceDocument] = Field(default_factory=list)
    research_notes: str | None = None
    analysis_notes: str | None = None
    final_answer: str | None = None

    judge_score: JudgeScore | None = None
    rewrite_count: int = 0
    rewrite_limit: int = 1

    agent_results: list[AgentResult] = Field(default_factory=list)
    trace: list[TraceEvent] = Field(default_factory=list)
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    errors: list[str] = Field(default_factory=list)

    def with_updates(self, **updates: Any) -> "ResearchState":
        """Return a copied state with explicit updates."""
        return self.model_copy(update=updates)

    def record_route_immutable(self, route: str) -> "ResearchState":
        """Return a copied state with updated route history and iteration."""
        return self.with_updates(
            route_history=[*self.route_history, route],
            iteration=self.iteration + 1,
        )

    def add_trace_event_immutable(self, name: str, payload: dict[str, Any]) -> "ResearchState":
        """Return a copied state with appended trace event."""
        event = TraceEvent(name=name, payload=payload)
        return self.with_updates(trace=[*self.trace, event])

    # Backward-compatible mutating helpers for existing tests/callers.
    def record_route(self, route: str) -> None:
        self.route_history.append(route)
        self.iteration += 1

    def add_trace_event(self, name: str, payload: dict[str, Any]) -> None:
        self.trace.append(TraceEvent(name=name, payload=payload))


def apply_route_decision(state: ResearchState, decision: RouteDecision) -> ResearchState:
    """Apply a routing decision to state immutably."""
    next_state = state.record_route_immutable(decision.next_agent)
    next_state = next_state.with_updates(stop_reason=decision.stop_reason)
    return next_state.add_trace_event_immutable(
        "route_decision",
        {
            "next_agent": decision.next_agent,
            "reason": decision.reason,
            "stop_reason": decision.stop_reason,
            "iteration": next_state.iteration,
        },
    )
