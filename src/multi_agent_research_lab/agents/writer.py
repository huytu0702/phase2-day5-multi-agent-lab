"""Writer agent implementation."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState


class WriterAgent(BaseAgent):
    """Produces final answer from research and analysis notes."""

    name = "writer"

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.final_answer`."""

        citation_list = [f"[{index}]" for index, _ in enumerate(state.sources, start=1)]
        citations = " ".join(citation_list) if citation_list else "[no-citations]"

        state.final_answer = "\n".join(
            [
                f"Answer for: {state.request.query}",
                "",
                "Summary:",
                "- Based on the collected sources and analysis, the response is evidence-backed but concise.",
                "",
                f"Citations: {citations}",
                "",
                "Limitations:",
                "- Source set may be incomplete.",
                "- Snippets may omit full context from original documents.",
            ]
        )

        state.judge_score = None

        state.agent_results.append(
            AgentResult(
                agent=AgentName.WRITER,
                content=state.final_answer,
                metadata={"citation_count": len(citation_list)},
                success=True,
            )
        )
        return state
