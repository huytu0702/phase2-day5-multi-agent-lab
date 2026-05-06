from multi_agent_research_lab.agents import SupervisorAgent
from multi_agent_research_lab.core.schemas import AgentName, JudgeScore, ResearchQuery, SourceDocument
from multi_agent_research_lab.core.state import ResearchState


def _state(**updates: object) -> ResearchState:
    base = ResearchState(request=ResearchQuery(query="Explain multi-agent systems"))
    return base.model_copy(update=updates)


def test_empty_state_routes_researcher() -> None:
    result = SupervisorAgent().run(_state())
    assert result.route_history[-1] == "researcher"
    assert result.stop_reason is None


def test_research_complete_routes_analyst() -> None:
    result = SupervisorAgent().run(
        _state(
            sources=[SourceDocument(title="t", snippet="s")],
            research_notes="notes",
        )
    )
    assert result.route_history[-1] == "analyst"


def test_analysis_complete_routes_writer() -> None:
    result = SupervisorAgent().run(
        _state(
            sources=[SourceDocument(title="t", snippet="s")],
            research_notes="notes",
            analysis_notes="analysis",
        )
    )
    assert result.route_history[-1] == "writer"


def test_final_answer_routes_judge() -> None:
    result = SupervisorAgent().run(
        _state(
            sources=[SourceDocument(title="t", snippet="s")],
            research_notes="notes",
            analysis_notes="analysis",
            final_answer="answer",
        )
    )
    assert result.route_history[-1] == "judge"


def test_judge_pass_routes_end() -> None:
    result = SupervisorAgent().run(
        _state(
            sources=[SourceDocument(title="t", snippet="s")],
            research_notes="notes",
            analysis_notes="analysis",
            final_answer="answer",
            judge_score=JudgeScore(score=8.5, passed=True),
        )
    )
    assert result.route_history[-1] == "end"
    assert result.stop_reason == "completed"


def test_max_iterations_routes_end_with_safe_stop() -> None:
    result = SupervisorAgent().run(
        _state(
            iteration=8,
            max_iterations=8,
            sources=[SourceDocument(title="t", snippet="s")],
            research_notes="notes",
            analysis_notes="analysis",
            final_answer="answer",
            judge_score=JudgeScore(score=2.0, passed=False),
        )
    )
    assert result.route_history[-1] == "end"
    assert result.stop_reason == "max_iterations"


def test_judge_fail_with_budget_routes_writer_once() -> None:
    result = SupervisorAgent().run(
        _state(
            sources=[SourceDocument(title="t", snippet="s")],
            research_notes="notes",
            analysis_notes="analysis",
            final_answer="answer",
            judge_score=JudgeScore(score=4.0, passed=False),
            rewrite_count=0,
            rewrite_limit=1,
        )
    )
    assert result.route_history[-1] == "writer"


def test_judge_fail_without_budget_stops() -> None:
    result = SupervisorAgent().run(
        _state(
            sources=[SourceDocument(title="t", snippet="s")],
            research_notes="notes",
            analysis_notes="analysis",
            final_answer="answer",
            judge_score=JudgeScore(score=4.0, passed=False),
            rewrite_count=1,
            rewrite_limit=1,
        )
    )
    assert result.route_history[-1] == "end"
    assert result.stop_reason == "validation_failed_with_limit"


def test_agent_result_supports_judge_agent_name() -> None:
    # guardrail for schema changes required by routing flow
    assert AgentName.JUDGE.value == "judge"
