"""Writer agent implementation."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient


class WriterAgent(BaseAgent):
    """Produces final answer from research and analysis notes."""

    name = "writer"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self._llm_client = llm_client or LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.final_answer`."""

        citation_lines = [
            f"[{index}] {source.title} - {source.url or 'no-url'}"
            for index, source in enumerate(state.sources, start=1)
        ]

        response = self._llm_client.complete(
            system_prompt=(
                "You are a research writing agent. Return a concise answer with clear evidence-based "
                "claims, explicit citations like [1], [2], and a short limitations section."
            ),
            user_prompt=(
                f"User query: {state.request.query}\n"
                f"Audience: {state.request.audience}\n\n"
                f"Research notes:\n{state.research_notes or 'N/A'}\n\n"
                f"Analysis notes:\n{state.analysis_notes or 'N/A'}\n\n"
                f"Available citations:\n" + "\n".join(citation_lines or ["No citations available"])
            ),
        )
        final_answer = response.content.strip()
        if "Citations:" not in final_answer:
            citation_tokens = [f"[{index}]" for index, _ in enumerate(state.sources, start=1)]
            final_answer = f"{final_answer}\n\nCitations: {' '.join(citation_tokens) if citation_tokens else '[no-citations]'}"
        if "Limitations:" not in final_answer:
            final_answer = f"{final_answer}\n\nLimitations:\n- Source set may be incomplete."
        state.final_answer = final_answer

        state.judge_score = None

        state.agent_results.append(
            AgentResult(
                agent=AgentName.WRITER,
                content=state.final_answer,
                metadata={"citation_count": len(citation_lines)},
                success=True,
            )
        )
        return state
