"""Benchmark utilities for baseline and multi-agent runs."""

from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter
from typing import Callable

from multi_agent_research_lab.core.schemas import BenchmarkMetrics
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.evaluation.report import render_markdown_report


Runner = Callable[[str], ResearchState]
Judge = Callable[[str, str], float]


def _estimate_citation_coverage(state: ResearchState) -> float:
    source_count = len(state.sources)
    if source_count == 0:
        return 0.0

    answer = state.final_answer or ""
    cited = sum(1 for index in range(1, source_count + 1) if f"[{index}]" in answer)
    return round(cited / source_count, 3)


def _estimate_quality_score(state: ResearchState) -> float | None:
    if state.judge_score is not None:
        return state.judge_score.score
    if state.final_answer:
        return 6.0 if state.sources else 4.0
    return None


def run_benchmark(run_name: str, query: str, runner: Runner) -> tuple[ResearchState, BenchmarkMetrics]:
    """Measure execution and compute core quality/cost metrics."""

    started = perf_counter()
    state = runner(query)
    latency = perf_counter() - started

    cost = state.token_usage.estimated_cost_usd
    quality = _estimate_quality_score(state)
    citation_coverage = _estimate_citation_coverage(state)
    failure_count = len(state.errors)
    mode = "baseline" if "baseline" in run_name.lower() else "multi-agent"

    metrics = BenchmarkMetrics(
        run_name=run_name,
        mode=mode,
        latency_seconds=latency,
        estimated_cost_usd=cost,
        quality_score=quality,
        source_count=len(state.sources),
        citation_coverage=citation_coverage,
        failure_count=failure_count,
        stop_reason=state.stop_reason,
        notes="ok" if failure_count == 0 else "completed_with_errors",
    )
    return state, metrics


def run_comparison(
    query: str,
    baseline_runner: Runner,
    multi_agent_runner: Runner,
    judge: Judge,
    metrics_output_path: str | Path,
    report_output_path: str | Path,
) -> list[BenchmarkMetrics]:
    """Run baseline and multi-agent, persist judged metrics and markdown report."""
    baseline_state, baseline_metrics = run_benchmark("baseline", query, baseline_runner)
    multi_state, multi_metrics = run_benchmark("multi-agent", query, multi_agent_runner)

    baseline_metrics.quality_score = max(0.0, min(10.0, judge(query, baseline_state.final_answer or "")))
    multi_metrics.quality_score = max(0.0, min(10.0, judge(query, multi_state.final_answer or "")))

    baseline_metrics.notes = "single-agent baseline"
    multi_metrics.notes = "multi-agent workflow"

    metrics = [baseline_metrics, multi_metrics]

    metrics_path = Path(metrics_output_path)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    with metrics_path.open("w", encoding="utf-8") as file_handle:
        json.dump([item.model_dump() for item in metrics], file_handle, indent=2)

    report_path = Path(report_output_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_markdown_report(metrics), encoding="utf-8")

    return metrics
