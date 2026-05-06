"""Analyst agent implementation."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient


class AnalystAgent(BaseAgent):
    """Turns research notes into structured insights."""

    name = "analyst"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self._llm_client = llm_client or LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.analysis_notes`."""

        citation_lines = [
            f"[{index}] {source.title}: {source.snippet.strip()}"
            for index, source in enumerate(state.sources, start=1)
            if source.snippet.strip()
        ]
        evidence = "\n".join(citation_lines) if citation_lines else "No evidence snippets available."

        response = self._llm_client.complete(
            system_prompt=(
                "You are an analysis agent. Produce concise analysis notes with sections: "
                "Claims, Evidence Quality, Gaps & Risks, Recommended Next Step."
            ),
            user_prompt=(
                f"Query: {state.request.query}\n"
                f"Research notes:\n{state.research_notes or 'N/A'}\n\n"
                f"Sources:\n{evidence}"
            ),
        )
        analysis_notes = response.content.strip()
        section_aliases = {
            "**Claims**": "Claims:",
            "Claims": "Claims:",
            "**Evidence Quality**": "Evidence Quality:",
            "Evidence Quality": "Evidence Quality:",
            "**Gaps & Risks**": "Gaps & Risks:",
            "Gaps & Risks": "Gaps & Risks:",
            "**Recommended Next Step**": "Recommended Next Step:",
            "Recommended Next Step": "Recommended Next Step:",
        }
        for source, target in section_aliases.items():
            analysis_notes = analysis_notes.replace(source, target)
        if "Analysis Notes" not in analysis_notes:
            analysis_notes = f"Analysis Notes\n\n{analysis_notes}"
        state.analysis_notes = analysis_notes

        state.agent_results.append(
            AgentResult(
                agent=AgentName.ANALYST,
                content=state.analysis_notes,
                metadata={"source_count": len(state.sources)},
                success=True,
            )
        )
        return state
