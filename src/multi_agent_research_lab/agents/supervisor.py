"""Supervisor / router implementation."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import RouteDecision
from multi_agent_research_lab.core.state import ResearchState, apply_route_decision


class SupervisorAgent(BaseAgent):
    """Decides which worker should run next and when to stop."""

    name = "supervisor"

    def run(self, state: ResearchState) -> ResearchState:
        """Route according to phase-3 deterministic policy."""
        decision = self._decide_route(state)
        return apply_route_decision(state, decision)

    def _decide_route(self, state: ResearchState) -> RouteDecision:
        if state.iteration >= state.max_iterations:
            return RouteDecision(
                next_agent="end",
                reason="Reached max iteration budget.",
                stop_reason="max_iterations",
            )

        if not state.sources or not state.research_notes:
            return RouteDecision(
                next_agent="researcher",
                reason="Sources or research notes are missing.",
            )

        if not state.analysis_notes:
            return RouteDecision(
                next_agent="analyst",
                reason="Analysis notes are missing.",
            )

        if not state.final_answer:
            return RouteDecision(
                next_agent="writer",
                reason="Final answer is missing.",
            )

        if state.judge_score is None:
            return RouteDecision(
                next_agent="judge",
                reason="Final answer exists but judge has not run.",
            )

        if state.judge_score.passed:
            return RouteDecision(
                next_agent="end",
                reason="Judge approved final answer.",
                stop_reason="completed",
            )

        if state.rewrite_count < state.rewrite_limit:
            return RouteDecision(
                next_agent="writer",
                reason="Judge failed but rewrite budget remains.",
            )

        return RouteDecision(
            next_agent="end",
            reason="Judge failed and rewrite budget exhausted.",
            stop_reason="validation_failed_with_limit",
        )
