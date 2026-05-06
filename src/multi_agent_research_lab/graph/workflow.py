"""LangGraph workflow implementation for the research lab."""

from __future__ import annotations

from typing import Any

from multi_agent_research_lab.agents.analyst import AnalystAgent
from multi_agent_research_lab.agents.critic import CriticAgent
from multi_agent_research_lab.agents.researcher import ResearcherAgent
from multi_agent_research_lab.agents.supervisor import SupervisorAgent
from multi_agent_research_lab.agents.writer import WriterAgent
from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.schemas import JudgeScore
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.observability.tracing import trace_span
from multi_agent_research_lab.services.search_client import SearchClient


class MultiAgentWorkflow:
    """Builds and runs the multi-agent graph.

    Keep orchestration here; keep agent internals in `agents/`.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._offline_mode = not bool(settings.tavily_api_key)
        self._supervisor = SupervisorAgent()
        self._researcher = ResearcherAgent(
            search_client=SearchClient(settings=settings) if settings.tavily_api_key else None
        )
        self._analyst = AnalystAgent()
        self._writer = WriterAgent()
        self._critic = CriticAgent()

    def build(self) -> object:
        """Create and compile a LangGraph graph when available."""

        try:
            from langgraph.graph import END, START, StateGraph
        except ImportError:
            return {
                "type": "sequential-fallback",
                "nodes": ["supervisor", "researcher", "analyst", "writer", "judge", "end"],
            }

        graph = StateGraph(ResearchState)
        graph.add_node("supervisor", self._supervisor_node)
        graph.add_node("researcher", self._researcher_node)
        graph.add_node("analyst", self._analyst_node)
        graph.add_node("writer", self._writer_node)
        graph.add_node("judge", self._judge_node)

        graph.add_edge(START, "supervisor")
        graph.add_edge("researcher", "supervisor")
        graph.add_edge("analyst", "supervisor")
        graph.add_edge("writer", "supervisor")
        graph.add_edge("judge", "supervisor")
        graph.add_conditional_edges(
            "supervisor",
            self._route_next,
            {
                "researcher": "researcher",
                "analyst": "analyst",
                "writer": "writer",
                "judge": "judge",
                "end": END,
            },
        )
        return graph.compile()

    def run(self, state: ResearchState) -> ResearchState:
        """Execute the graph and return final state."""

        app = self.build()
        if hasattr(app, "invoke"):
            result = app.invoke(state)
            if isinstance(result, ResearchState):
                return result
            if isinstance(result, dict):
                return ResearchState.model_validate(result)

        current_state = state
        while True:
            current_state = self._supervisor_node(current_state)
            route = current_state.route_history[-1] if current_state.route_history else "end"
            if route == "end":
                return current_state
            if route == "researcher":
                current_state = self._researcher_node(current_state)
            elif route == "analyst":
                current_state = self._analyst_node(current_state)
            elif route == "writer":
                current_state = self._writer_node(current_state)
            elif route == "judge":
                current_state = self._judge_node(current_state)

    def _route_next(self, state: ResearchState) -> str:
        return state.route_history[-1] if state.route_history else "end"

    def _supervisor_node(self, state: ResearchState) -> ResearchState:
        with trace_span("workflow.supervisor") as span:
            next_state = self._supervisor.run(state)
            span["attributes"]["route"] = next_state.route_history[-1] if next_state.route_history else "end"
            return next_state

    def _researcher_node(self, state: ResearchState) -> ResearchState:
        with trace_span("workflow.researcher"):
            return self._researcher.run(state)

    def _analyst_node(self, state: ResearchState) -> ResearchState:
        with trace_span("workflow.analyst"):
            return self._analyst.run(state)

    def _writer_node(self, state: ResearchState) -> ResearchState:
        with trace_span("workflow.writer"):
            return self._writer.run(state)

    def _judge_node(self, state: ResearchState) -> ResearchState:
        with trace_span("workflow.judge") as span:
            next_state = self._critic.run(state)
            judge_result = next(
                (result for result in reversed(next_state.agent_results) if result.agent.value == "judge"),
                None,
            )
            if judge_result is None:
                return next_state

            metadata: dict[str, Any] = dict(judge_result.metadata)
            next_state.judge_score = JudgeScore(
                score=float(metadata.get("score", 0.0)),
                passed=bool(metadata.get("passed", False)),
                rationale=str(metadata.get("rationale", "")),
            )
            if not next_state.judge_score.passed:
                next_state.rewrite_count += 1
            span["attributes"]["passed"] = next_state.judge_score.passed
            return next_state
