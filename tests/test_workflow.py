from multi_agent_research_lab.core.schemas import ResearchQuery
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow


def test_workflow_build_returns_compiled_or_fallback_object() -> None:
    workflow = MultiAgentWorkflow()
    built = workflow.build()
    assert built is not None


def test_workflow_run_completes_and_sets_judge_score() -> None:
    state = ResearchState(request=ResearchQuery(query="Explain multi-agent workflow patterns"))
    result = MultiAgentWorkflow().run(state)

    assert result.stop_reason == "completed"
    assert result.final_answer is not None
    assert result.judge_score is not None
    assert result.judge_score.passed is True
    assert "end" in result.route_history
