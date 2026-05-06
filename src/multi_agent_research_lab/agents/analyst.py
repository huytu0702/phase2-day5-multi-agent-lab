"""Analyst agent implementation."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState


class AnalystAgent(BaseAgent):
    """Turns research notes into structured insights."""

    name = "analyst"

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.analysis_notes`."""

        source_count = len(state.sources)
        citations = [f"[{index}]" for index in range(1, source_count + 1)]
        citation_text = ", ".join(citations) if citations else "none"

        state.analysis_notes = "\n".join(
            [
                "Analysis Notes",
                "Claims:",
                f"- The available evidence contains {source_count} source(s).",
                "",
                "Evidence Quality:",
                f"- Citation coverage appears in references: {citation_text}.",
                "",
                "Gaps & Risks:",
                "- Additional primary sources may be needed for stronger confidence.",
                "",
                "Recommended Next Step:",
                "- Draft a concise answer that includes explicit citations and limitations.",
            ]
        )

        state.agent_results.append(
            AgentResult(
                agent=AgentName.ANALYST,
                content=state.analysis_notes,
                metadata={"source_count": source_count},
                success=True,
            )
        )
        return state
