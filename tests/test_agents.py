from multi_agent_research_lab.agents.analyst import AnalystAgent
from multi_agent_research_lab.agents.critic import CriticAgent
from multi_agent_research_lab.agents.researcher import ResearcherAgent
from multi_agent_research_lab.agents.writer import WriterAgent
from multi_agent_research_lab.core.schemas import AgentName, ResearchQuery, SourceDocument
from multi_agent_research_lab.core.state import ResearchState


class FakeSearchClient:
    def search(self, query: str, max_results: int = 5) -> list[SourceDocument]:
        _ = (query, max_results)
        return [
            SourceDocument(
                title="Source A",
                url="https://example.com/a",
                snippet="A factual snippet from source A.",
            ),
            SourceDocument(
                title="Source B",
                url="https://example.com/b",
                snippet="A factual snippet from source B.",
            ),
        ]


def _make_state() -> ResearchState:
    return ResearchState(request=ResearchQuery(query="Explain multi-agent systems", max_sources=2))


def test_researcher_uses_search_client_outputs_and_generates_citations() -> None:
    state = _make_state()

    next_state = ResearcherAgent(search_client=FakeSearchClient()).run(state)

    assert len(next_state.sources) == 2
    assert next_state.research_notes is not None
    assert "Citations:" in next_state.research_notes
    assert "[1] Source A - https://example.com/a" in next_state.research_notes
    assert next_state.agent_results[-1].agent == AgentName.RESEARCHER


def test_analyst_produces_structured_analysis_notes() -> None:
    state = _make_state()
    state = ResearcherAgent(search_client=FakeSearchClient()).run(state)

    next_state = AnalystAgent().run(state)

    assert next_state.analysis_notes is not None
    assert "Analysis Notes" in next_state.analysis_notes
    assert "Claims:" in next_state.analysis_notes
    assert "Evidence Quality:" in next_state.analysis_notes
    assert "Gaps & Risks:" in next_state.analysis_notes
    assert next_state.agent_results[-1].agent == AgentName.ANALYST


def test_writer_produces_final_answer_with_citations_and_limitations() -> None:
    state = _make_state()
    state = ResearcherAgent(search_client=FakeSearchClient()).run(state)
    state = AnalystAgent().run(state)

    next_state = WriterAgent().run(state)

    assert next_state.final_answer is not None
    assert "Citations:" in next_state.final_answer
    assert "[1]" in next_state.final_answer
    assert "Limitations:" in next_state.final_answer
    assert next_state.agent_results[-1].agent == AgentName.WRITER


def test_critic_returns_structured_score_and_pass_fail() -> None:
    state = _make_state()
    state = ResearcherAgent(search_client=FakeSearchClient()).run(state)
    state = AnalystAgent().run(state)
    state = WriterAgent().run(state)

    next_state = CriticAgent().run(state)

    result = next_state.agent_results[-1]
    assert result.agent == AgentName.JUDGE
    assert isinstance(result.metadata["score"], float)
    assert isinstance(result.metadata["passed"], bool)
    assert isinstance(result.metadata["rationale"], str)
