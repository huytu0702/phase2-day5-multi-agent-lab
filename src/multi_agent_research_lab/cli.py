"""Command-line entrypoint for the lab starter."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel

from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.schemas import ResearchQuery, SourceDocument
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.evaluation.benchmark import run_comparison
from multi_agent_research_lab.evaluation.report import render_markdown_report
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow
from multi_agent_research_lab.observability.logging import configure_logging

app = typer.Typer(help="Multi-Agent Research Lab starter CLI")
console = Console()


def _init() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)


@app.command()
def baseline(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Run a deterministic single-agent baseline."""

    _init()
    settings = get_settings()
    request = ResearchQuery(query=query)
    state = ResearchState(request=request, max_iterations=settings.max_iterations)
    state.sources = [
        SourceDocument(
            title="Baseline synthetic source",
            url=None,
            snippet="This baseline response is deterministic and lightweight.",
        )
    ]
    state.final_answer = (
        f"Baseline answer for: {query}\n\n"
        "Summary: this is a single-pass response without iterative coordination.\n"
        "Citations: [1]"
    )
    state.stop_reason = "completed"
    console.print(Panel.fit(state.final_answer, title="Single-Agent Baseline"))


@app.command("multi-agent")
def multi_agent(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Run the multi-agent workflow."""

    _init()
    settings = get_settings()
    state = ResearchState(request=ResearchQuery(query=query), max_iterations=settings.max_iterations)
    workflow = MultiAgentWorkflow()
    result = workflow.run(state)
    console.print(result.model_dump_json(indent=2))


@app.command("benchmark")
def benchmark(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
    metrics_out: Annotated[str, typer.Option("--metrics-out", help="Metrics JSON output path")] = "reports/benchmark_metrics.json",
    report_out: Annotated[str, typer.Option("--report-out", help="Markdown report output path")] = "reports/benchmark_report.md",
) -> None:
    """Run baseline and multi-agent benchmarks and persist report artifacts."""

    _init()
    settings = get_settings()

    def baseline_runner(prompt: str) -> ResearchState:
        base_state = ResearchState(request=ResearchQuery(query=prompt), max_iterations=settings.max_iterations)
        base_state.sources = [
            SourceDocument(
                title="Baseline synthetic source",
                snippet="Single-pass baseline run.",
            )
        ]
        base_state.final_answer = f"Baseline answer for: {prompt}\n\nCitations: [1]"
        base_state.stop_reason = "completed"
        return base_state

    def multi_runner(prompt: str) -> ResearchState:
        return MultiAgentWorkflow().run(
            ResearchState(request=ResearchQuery(query=prompt), max_iterations=settings.max_iterations)
        )

    def judge_runner(_prompt: str, answer: str) -> float:
        if not answer.strip():
            return 0.0
        score = 5.0
        if "[" in answer and "]" in answer:
            score += 2.0
        if "Summary" in answer:
            score += 1.5
        return min(10.0, score)

    metrics = run_comparison(
        query=query,
        baseline_runner=baseline_runner,
        multi_agent_runner=multi_runner,
        judge=judge_runner,
        metrics_output_path=Path(metrics_out),
        report_output_path=Path(report_out),
    )

    console.print(render_markdown_report(metrics))
    console.print(Panel.fit(f"Saved metrics to {metrics_out} and report to {report_out}", title="Benchmark"))


if __name__ == "__main__":
    app()
