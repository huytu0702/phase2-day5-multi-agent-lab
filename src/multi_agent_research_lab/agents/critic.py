"""Critic (judge-style) agent implementation."""

import re

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState


class CriticAgent(BaseAgent):
    """Fact-checking and quality review agent returning pass/fail."""

    name = "critic"

    def run(self, state: ResearchState) -> ResearchState:
        """Validate final answer and append a structured score."""

        has_answer = bool(state.final_answer and state.final_answer.strip())
        source_count = len(state.sources)
        citation_matches = re.findall(r"\[\d+\]", state.final_answer or "")
        has_citations = has_answer and len(citation_matches) > 0

        score = 0.0
        if has_answer:
            score += 5.0
        if has_citations:
            score += 3.0
        if source_count > 0:
            score += 2.0

        passed = score >= 7.0
        rationale = (
            "Answer exists, includes citations, and has at least one source."
            if passed
            else "Response quality is insufficient: missing answer content, citations, or sources."
        )

        verdict = {
            "score": round(score, 2),
            "passed": passed,
            "rationale": rationale,
        }

        state.agent_results.append(
            AgentResult(
                agent=AgentName.JUDGE,
                content=rationale,
                metadata=verdict,
                success=True,
            )
        )
        return state
