"""Critic (judge-style) agent implementation."""

import json

from pydantic import BaseModel, Field

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient


class _JudgeVerdict(BaseModel):
    score: float = Field(..., ge=0, le=10)
    passed: bool
    rationale: str


class CriticAgent(BaseAgent):
    """Fact-checking and quality review agent returning pass/fail."""

    name = "critic"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self._llm_client = llm_client or LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Validate final answer and append a structured score."""

        source_lines = [
            f"[{index}] {source.title} - {source.url or 'no-url'}"
            for index, source in enumerate(state.sources, start=1)
        ]
        verdict = self._llm_client.complete_structured(
            system_prompt=(
                "You are a strict judge for research answers. Score from 0-10 and return JSON only "
                "with keys: score, passed, rationale. Set passed=true only when answer is clear, "
                "supported by provided citations, and limitations are acknowledged."
            ),
            user_prompt=(
                f"Query: {state.request.query}\n\n"
                f"Final answer:\n{state.final_answer or 'N/A'}\n\n"
                f"Sources:\n" + "\n".join(source_lines or ["No sources"])
            ),
            response_model=_JudgeVerdict,
        )

        metadata = json.loads(verdict.model_dump_json())
        state.agent_results.append(
            AgentResult(
                agent=AgentName.JUDGE,
                content=verdict.rationale,
                metadata=metadata,
                success=True,
            )
        )
        return state
