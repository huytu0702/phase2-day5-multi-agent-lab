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
from multi_agent_research_lab.observability.tracing import trace_run, trace_span
from multi_agent_research_lab.services.llm_client import LLMClient
from multi_agent_research_lab.services.search_client import SearchClient


class MultiAgentWorkflow:
    """Builds and runs the multi-agent graph.

    Keep orchestration here; keep agent internals in `agents/`.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._offline_mode = not bool(settings.tavily_api_key)
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required to run multi-agent LLM workflow")

        llm_client = LLMClient(settings=settings)
        self._supervisor = SupervisorAgent()
        self._researcher = ResearcherAgent(
            search_client=SearchClient(settings=settings) if settings.tavily_api_key else None
        )
        self._analyst = AnalystAgent(llm_client=llm_client)
        self._writer = WriterAgent(llm_client=llm_client)
        self._critic = CriticAgent(llm_client=llm_client)
        self._active_trace_context: Any | None = None

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

        run_metadata = {"query": state.request.query, "max_iterations": state.max_iterations}
        with trace_run("workflow.run", metadata=run_metadata) as trace_context:
            previous_trace_context = self._active_trace_context
            self._active_trace_context = trace_context
            app = self.build()
            try:
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
            finally:
                self._active_trace_context = previous_trace_context

    def _route_next(self, state: ResearchState) -> str:
        return state.route_history[-1] if state.route_history else "end"

    def _supervisor_node(self, state: ResearchState) -> ResearchState:
        with trace_span("workflow.supervisor", trace_context=self._active_trace_context) as span:
            span["input"] = {
                "iteration": state.iteration,
                "route_history": list(state.route_history),
                "has_sources": bool(state.sources),
                "has_research_notes": bool(state.research_notes),
                "has_analysis_notes": bool(state.analysis_notes),
                "has_final_answer": bool(state.final_answer),
            }
            next_state = self._supervisor.run(state)
            route = next_state.route_history[-1] if next_state.route_history else "end"
            span["attributes"]["route"] = route
            span["output"] = {"route": route, "stop_reason": next_state.stop_reason}
            return next_state

    def _researcher_node(self, state: ResearchState) -> ResearchState:
        with trace_span("workflow.researcher", trace_context=self._active_trace_context) as span:
            span["input"] = {"query": state.request.query, "max_sources": state.request.max_sources}
            next_state = self._researcher.run(state)
            span["output"] = {
                "source_count": len(next_state.sources),
                "has_research_notes": bool(next_state.research_notes),
            }
            return next_state

    def _analyst_node(self, state: ResearchState) -> ResearchState:
        with trace_span("workflow.analyst", trace_context=self._active_trace_context) as span:
            span["input"] = {
                "source_count": len(state.sources),
                "has_research_notes": bool(state.research_notes),
            }
            next_state = self._analyst.run(state)
            span["output"] = {"has_analysis_notes": bool(next_state.analysis_notes)}
            return next_state

    def _writer_node(self, state: ResearchState) -> ResearchState:
        with trace_span("workflow.writer", trace_context=self._active_trace_context) as span:
            span["input"] = {
                "has_analysis_notes": bool(state.analysis_notes),
                "source_count": len(state.sources),
            }
            next_state = self._writer.run(state)
            span["output"] = {
                "has_final_answer": bool(next_state.final_answer),
                "final_answer": next_state.final_answer or "",
            }
            return next_state

    def _judge_node(self, state: ResearchState) -> ResearchState:
        with trace_span("workflow.judge", trace_context=self._active_trace_context) as span:
            span["input"] = {
                "has_final_answer": bool(state.final_answer),
                "source_count": len(state.sources),
            }
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
            span["output"] = {
                "score": next_state.judge_score.score,
                "passed": next_state.judge_score.passed,
                "rationale": next_state.judge_score.rationale,
            }
            return next_state
