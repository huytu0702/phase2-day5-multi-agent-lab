"""Public schemas exchanged between CLI, agents, and evaluators."""

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class AgentName(StrEnum):
    SUPERVISOR = "supervisor"
    RESEARCHER = "researcher"
    ANALYST = "analyst"
    WRITER = "writer"
    JUDGE = "judge"
    CRITIC = "critic"


class ResearchQuery(BaseModel):
    query: str = Field(..., min_length=5)
    max_sources: int = Field(default=5, ge=1, le=20)
    audience: str = "technical learners"


class RouteDecision(BaseModel):
    next_agent: Literal["researcher", "analyst", "writer", "judge", "end"]
    reason: str
    stop_reason: str | None = None


class AgentResult(BaseModel):
    agent: AgentName
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    success: bool = True


class SourceDocument(BaseModel):
    title: str
    url: str | None = None
    snippet: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0


class TraceEvent(BaseModel):
    name: str
    payload: dict[str, Any] = Field(default_factory=dict)


class JudgeScore(BaseModel):
    score: float = Field(..., ge=0, le=10)
    passed: bool
    rationale: str = ""


class EvaluationResult(BaseModel):
    query: str
    judge_score: JudgeScore | None = None
    citation_coverage: float = Field(default=0.0, ge=0.0, le=1.0)
    failure_count: int = 0


class BenchmarkMetrics(BaseModel):
    run_name: str
    mode: Literal["baseline", "multi-agent"] = "multi-agent"
    latency_seconds: float
    estimated_cost_usd: float | None = None
    quality_score: float | None = Field(default=None, ge=0, le=10)
    source_count: int = 0
    citation_coverage: float = Field(default=0.0, ge=0.0, le=1.0)
    failure_count: int = 0
    stop_reason: str | None = None
    notes: str = ""
