"""Benchmark report rendering."""

from __future__ import annotations

from multi_agent_research_lab.core.schemas import BenchmarkMetrics


def render_markdown_report(metrics: list[BenchmarkMetrics]) -> str:
    """Render benchmark metrics to markdown."""

    lines = [
        "# Benchmark Report",
        "",
        "| Run | Mode | Latency (s) | Cost (USD) | Quality | Sources | Citation Coverage | Failures | Stop Reason | Notes |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|---|",
    ]

    for item in metrics:
        cost = "" if item.estimated_cost_usd is None else f"{item.estimated_cost_usd:.4f}"
        quality = "" if item.quality_score is None else f"{item.quality_score:.1f}"
        lines.append(
            "| "
            f"{item.run_name} | {item.mode} | {item.latency_seconds:.2f} | {cost} | {quality} "
            f"| {item.source_count} | {item.citation_coverage:.2f} | {item.failure_count} "
            f"| {item.stop_reason or ''} | {item.notes} |"
        )

    if metrics:
        avg_latency = sum(item.latency_seconds for item in metrics) / len(metrics)
        avg_quality_values = [item.quality_score for item in metrics if item.quality_score is not None]
        avg_quality = sum(avg_quality_values) / len(avg_quality_values) if avg_quality_values else None
        lines.extend(
            [
                "",
                "## Summary",
                f"- Runs: {len(metrics)}",
                f"- Average latency: {avg_latency:.2f}s",
                f"- Average quality: {avg_quality:.2f}" if avg_quality is not None else "- Average quality: N/A",
            ]
        )

    return "\n".join(lines) + "\n"
