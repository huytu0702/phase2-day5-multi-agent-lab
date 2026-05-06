from multi_agent_research_lab.core.schemas import JudgeScore, ResearchQuery, SourceDocument
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.evaluation.benchmark import run_benchmark


def _runner_with_judge(query: str) -> ResearchState:
    state = ResearchState(request=ResearchQuery(query=query))
    state.sources = [
        SourceDocument(title="s1", snippet="a"),
        SourceDocument(title="s2", snippet="b"),
    ]
    state.final_answer = "Answer with citations [1] [2]"
    state.judge_score = JudgeScore(score=8.0, passed=True, rationale="good")
    state.stop_reason = "completed"
    state.token_usage.estimated_cost_usd = 0.0123
    return state


def test_run_benchmark_computes_quality_and_coverage() -> None:
    state, metrics = run_benchmark("multi-agent", "Explain test strategy", _runner_with_judge)

    assert state.final_answer is not None
    assert metrics.mode == "multi-agent"
    assert metrics.quality_score == 8.0
    assert metrics.citation_coverage == 1.0
    assert metrics.source_count == 2
    assert metrics.estimated_cost_usd == 0.0123
    assert metrics.failure_count == 0
    assert metrics.stop_reason == "completed"


def test_run_benchmark_infers_baseline_mode() -> None:
    _, metrics = run_benchmark("baseline-v1", "Explain test strategy", _runner_with_judge)
    assert metrics.mode == "baseline"
