# Production Implementation Plan: Multi-Agent Research Lab

## 1. Confirmed requirements

Người dùng đã xác nhận các ràng buộc triển khai sau:

1. `.env` đã có API keys hợp lệ.
2. Model LLM dùng cho runtime thực tế: `gpt-5.4-mini`.
3. `.env` đã có `TAVILY_API_KEY`, nên search phải dùng Tavily thật.
4. Bắt buộc dùng LangGraph cho workflow multi-agent.
5. Cho phép dùng LLM-as-judge để chấm quality score trong benchmark.
6. Nếu dùng Langfuse thì phải dùng Langfuse SDK v4.

## 2. Goal

Hoàn thiện starter repo thành hệ thống production-grade cho lab Multi-Agent Systems, gồm:

- Single-agent baseline chạy LLM thật.
- Multi-agent workflow chạy bằng LangGraph thật.
- Các agent rõ vai trò: Supervisor, Researcher, Analyst, Writer, optional Critic/Judge.
- Search thật qua Tavily.
- Trace đầy đủ, ưu tiên Langfuse SDK v4 nếu cấu hình có sẵn; luôn có fallback local JSON trace.
- Benchmark baseline vs multi-agent theo quality, latency, token/cost, citation coverage, failure rate.
- Sinh `reports/benchmark_report.md` và trace artifacts để nộp bài.

## 3. Scoring strategy

Theo rubric lab, mục tiêu là đạt tối đa 10/10 và có bonus.

| Rubric area | Strategy |
|---|---|
| Role clarity | Mỗi agent có prompt, input, output, schema riêng. Supervisor chỉ route, Researcher chỉ thu thập/tóm tắt nguồn, Analyst chỉ phân tích, Writer chỉ viết câu trả lời cuối. |
| State design | Shared state chứa query, sources, research notes, analysis notes, final answer, routing history, trace events, retries, token usage, cost, validation status, stop reason. |
| Failure guards | Enforce max iterations, per-call timeout, retry transient errors, Pydantic validation, safe stop, fallback có trace rõ ràng. |
| Benchmark | Chạy baseline và multi-agent trên nhiều query; report latency, token/cost, citation coverage, failure rate, LLM-as-judge quality. |
| Trace explanation | Langfuse trace nếu có config; local JSON trace luôn được xuất ra, ghi rõ agent, duration, route, input/output summary, error/fallback. |

Bonus target:

- LangGraph workflow thật thay vì loop thủ công.
- Tavily search thật.
- LLM-as-judge quality evaluation.
- Optional Critic/Judge node trong LangGraph.
- Langfuse SDK v4 tracing nếu env có cấu hình.
- Report có failure mode và cách khắc phục.

## 4. Target architecture

```text
CLI
├── baseline
│   └── Query -> Single LLM call -> Final answer -> Metrics -> Trace
│
├── multi-agent
│   └── LangGraph StateGraph
│       ├── Supervisor node
│       ├── Researcher node -> Tavily search + LLM research summary
│       ├── Analyst node -> structured analysis
│       ├── Writer node -> final answer with citations
│       └── Judge/Critic node -> validation + quality/citation checks
│
└── benchmark
    ├── Run baseline on query set
    ├── Run multi-agent on query set
    ├── Run LLM-as-judge
    ├── Export traces
    └── Render reports/benchmark_report.md
```

## 5. Proposed LangGraph flow

```text
START
  -> supervisor
  -> conditional route:
      researcher if sources/research_notes missing
      analyst if analysis_notes missing
      writer if final_answer missing
      judge if final_answer exists but quality not validated
      END if valid or max_iterations reached

researcher -> supervisor
analyst    -> supervisor
writer     -> supervisor
judge      -> supervisor or END
```

Routing rules:

1. If `iteration_count >= max_iterations`, stop safely with `stop_reason=max_iterations`.
2. If no sources or no research notes, route to `researcher`.
3. If no analysis notes, route to `analyst`.
4. If no final answer, route to `writer`.
5. If final answer exists and judge has not run, route to `judge`.
6. If judge passes, route to `END`.
7. If judge fails and rewrite budget remains, route to `writer` once.
8. Otherwise stop with `stop_reason=validation_failed_with_limit`.

## 6. Files to modify

### Core

- `src/multi_agent_research_lab/core/config.py`
  - Load model default `gpt-5.4-mini`.
  - Add OpenAI timeout/retry settings.
  - Add Tavily timeout/max results settings.
  - Add LangGraph max iterations.
  - Add benchmark and judge config.
  - Add Langfuse v4 config fields if needed.

- `src/multi_agent_research_lab/core/schemas.py`
  - Add or refine schemas:
    - `LLMResponse`
    - `SourceDocument`
    - `RouteDecision`
    - `AgentResult`
    - `TraceEvent`
    - `TokenUsage`
    - `BenchmarkMetrics`
    - `JudgeScore`
    - `EvaluationResult`

- `src/multi_agent_research_lab/core/state.py`
  - Define LangGraph-compatible state.
  - Keep updates explicit and preferably immutable.
  - Include trace, routing history, retries, token usage, cost, validation status.

### Services

- `src/multi_agent_research_lab/services/llm_client.py`
  - Implement real OpenAI-compatible LLM calls with model `gpt-5.4-mini`.
  - Use `.env`, never hard-code secrets.
  - Add retry, timeout, structured response helpers, token/cost metadata.

- `src/multi_agent_research_lab/services/search_client.py`
  - Implement Tavily search using `TAVILY_API_KEY`.
  - Normalize Tavily results into `SourceDocument`.
  - Validate empty/invalid results and record recoverable errors.

- `src/multi_agent_research_lab/services/storage.py`
  - Save benchmark report and trace artifacts under `reports/`.

### Agents

- `src/multi_agent_research_lab/agents/supervisor.py`
  - Implement deterministic routing compatible with LangGraph conditional edges.
  - Record route decisions and stop reasons.

- `src/multi_agent_research_lab/agents/researcher.py`
  - Use Tavily search.
  - Deduplicate and rank sources.
  - Ask LLM to summarize evidence with citations.

- `src/multi_agent_research_lab/agents/analyst.py`
  - Convert research notes into claims, trade-offs, confidence, gaps, risks.

- `src/multi_agent_research_lab/agents/writer.py`
  - Produce final answer with citations, limitations, and clear structure.

- `src/multi_agent_research_lab/agents/critic.py` or `judge.py`
  - LLM-as-judge and citation validation.
  - Return structured score and pass/fail decision.

### Graph

- `src/multi_agent_research_lab/graph/workflow.py`
  - Build real LangGraph `StateGraph`.
  - Add nodes and conditional edges.
  - Enforce max iterations and safe termination.
  - Return final state and trace path.

### Observability

- `src/multi_agent_research_lab/observability/tracing.py`
  - Always support local JSON traces.
  - If Langfuse env exists, use Langfuse SDK v4.
  - Trace each node with duration, model, token usage, route, status, error metadata.

### Evaluation

- `src/multi_agent_research_lab/evaluation/benchmark.py`
  - Run baseline and multi-agent on query set.
  - Collect latency, tokens, estimated cost, citation coverage, failure rate.
  - Call LLM-as-judge for quality score.

- `src/multi_agent_research_lab/evaluation/report.py`
  - Render `reports/benchmark_report.md`.
  - Include table, qualitative comparison, failure modes, trace artifact paths.

### CLI

- `src/multi_agent_research_lab/cli.py`
  - Ensure commands:
    - `baseline`
    - `multi-agent`
    - `benchmark`
  - Add CLI options:
    - `--query`
    - `--output-dir`
    - `--max-sources`
    - `--max-iterations`
    - `--enable-langfuse`

### Docs and reports

- `docs/design_template.md`
  - Fill with final design, roles, shared state, routing, guardrails, benchmark plan.

- `reports/benchmark_report.md`
  - Generated benchmark deliverable.

- `reports/traces/*.json`
  - Local trace artifacts.

## 7. TDD plan

### Unit tests first

Add/update tests before implementation:

- `tests/test_llm_client.py`
  - Missing key fails fast with clear error.
  - Mock successful LLM response.
  - Retry transient failure.
  - Model defaults to `gpt-5.4-mini` when not overridden.

- `tests/test_search_client.py`
  - Tavily result maps to `SourceDocument`.
  - Empty Tavily result is handled explicitly.
  - Invalid result does not crash workflow.

- `tests/test_supervisor_routing.py`
  - Empty state routes researcher.
  - Research complete routes analyst.
  - Analysis complete routes writer.
  - Final answer routes judge.
  - Valid judge result routes END.
  - Max iterations routes END with safe stop.

- `tests/test_agents.py`
  - Researcher populates sources and research notes.
  - Analyst populates analysis notes.
  - Writer includes citations.
  - Judge returns structured score.

### Integration tests

- `tests/test_workflow.py`
  - Full mocked LangGraph happy path.
  - Agent failure records trace and stops safely or retries.
  - Max iterations prevents infinite loop.

- `tests/test_benchmark.py`
  - Benchmark compares baseline and multi-agent.
  - Report includes required metrics.
  - LLM-as-judge score is persisted.

- `tests/test_tracing.py`
  - Local JSON trace is written.
  - Langfuse exporter can be mocked using SDK v4-compatible interface.

### Manual real-LLM smoke tests

Real LLM/search calls should be manual smoke tests, not mandatory unit tests:

```bash
python -m multi_agent_research_lab.cli baseline \
  --query "Research GraphRAG state-of-the-art and write a 500-word summary"

python -m multi_agent_research_lab.cli multi-agent \
  --query "Research GraphRAG state-of-the-art and write a 500-word summary"

python -m multi_agent_research_lab.cli benchmark --output-dir reports
```

## 8. Implementation phases

### Phase 1: dependency and current-code audit

1. Inspect `pyproject.toml` for dependencies.
2. Confirm versions for LangGraph, OpenAI SDK, Tavily client, Langfuse SDK v4.
3. Add missing dependencies only if necessary.
4. Search all `TODO(student)` markers and map them to implementation tasks.

Validation:

```bash
python -m multi_agent_research_lab.cli --help
pytest -q
```

### Phase 2: LLM and Tavily services

1. Write tests for LLM and search clients.
2. Implement OpenAI-compatible client using `gpt-5.4-mini`.
3. Implement Tavily search client.
4. Add structured schemas and explicit errors.

Validation:

```bash
pytest tests/test_llm_client.py tests/test_search_client.py -q
```

### Phase 3: state and agents

1. Extend shared state and schemas.
2. Implement Supervisor routing.
3. Implement Researcher, Analyst, Writer.
4. Implement Judge/Critic for LLM-as-judge.

Validation:

```bash
pytest tests/test_supervisor_routing.py tests/test_agents.py -q
```

### Phase 4: LangGraph workflow

1. Build `StateGraph` with nodes and conditional edges.
2. Add max iteration guard.
3. Add timeout/retry wrappers.
4. Ensure final state is serializable.

Validation:

```bash
pytest tests/test_workflow.py -q
python -m multi_agent_research_lab.cli multi-agent \
  --query "Research GraphRAG state-of-the-art and write a 500-word summary"
```

### Phase 5: tracing

1. Implement local JSON trace export.
2. Implement Langfuse SDK v4 exporter if env is configured.
3. Trace baseline, each LangGraph node, judge, benchmark runs.

Validation:

```bash
pytest tests/test_tracing.py -q
```

### Phase 6: benchmark and report

1. Implement benchmark runner.
2. Add at least 3 benchmark queries.
3. Add LLM-as-judge scoring.
4. Generate `reports/benchmark_report.md`.
5. Save trace artifacts.

Validation:

```bash
pytest tests/test_benchmark.py -q
python -m multi_agent_research_lab.cli benchmark --output-dir reports
```

### Phase 7: docs and final hardening

1. Fill `docs/design_template.md`.
2. Ensure README commands still work.
3. Run full test/lint/type checks.
4. Run real LLM smoke test.
5. Run code review and security review agents.

Validation:

```bash
pytest --cov=src --cov-report=term-missing
ruff check src tests
ruff format --check src tests
mypy src
python -m multi_agent_research_lab.cli --help
python -m multi_agent_research_lab.cli benchmark --output-dir reports
```

## 9. Guardrails

Required guardrails:

- `max_iterations` at workflow level.
- Per-call timeout for LLM and Tavily.
- Retry transient API failures.
- Pydantic validation for structured outputs.
- Safe stop reason for failures.
- No infinite loops in LangGraph.
- No secret logging.
- Trace all fallbacks/errors.

Recommended constants/config:

- `DEFAULT_MODEL=gpt-5.4-mini`
- `DEFAULT_MAX_ITERATIONS=8`
- `DEFAULT_OPENAI_TIMEOUT_SECONDS=60`
- `DEFAULT_TAVILY_TIMEOUT_SECONDS=30`
- `DEFAULT_MAX_RETRIES=2`
- `DEFAULT_MAX_SOURCES=5`
- `DEFAULT_JUDGE_REWRITE_LIMIT=1`

## 10. Benchmark metrics

Each run should collect:

- `mode`: baseline or multi-agent.
- `query`.
- `latency_seconds`.
- `total_tokens`.
- `prompt_tokens`.
- `completion_tokens`.
- `estimated_cost_usd`.
- `source_count`.
- `citation_coverage`.
- `quality_score` from LLM-as-judge.
- `failure_count`.
- `stop_reason`.
- `trace_path`.

Report should include:

- Summary table.
- Average metrics by mode.
- Best/worst examples.
- Quality comparison.
- Cost/latency tradeoff.
- Failure modes and fixes.
- Trace artifact links/paths.

## 11. Langfuse SDK v4 requirement

If Langfuse is enabled:

- Use Langfuse SDK v4 only.
- Keep Langfuse optional and environment-driven.
- Do not fail the whole workflow if Langfuse export fails; record local trace regardless.
- Never log API keys or secrets.

Expected env-driven behavior:

- If Langfuse public/secret keys and host are configured, export spans to Langfuse.
- If not configured, skip Langfuse and write local JSON traces only.

## 12. Risks and mitigations

| Risk | Mitigation |
|---|---|
| `gpt-5.4-mini` model name unsupported by installed SDK/provider | Fail fast with clear error and allow config override from `.env`. |
| Tavily returns sparse/no results | Record empty result, let Researcher explain source limitations, still continue safely if possible. |
| LLM output violates schema | Retry with validation error context, then safe stop if still invalid. |
| LangGraph conditional route loops | Hard max iterations and route history inspection. |
| Langfuse SDK v4 API mismatch | Isolate Langfuse exporter behind a small adapter and test with mocks. |
| Benchmark costs too much | Limit query count, max sources, and max output tokens. |
| Real API tests are flaky | Keep CI tests mocked; real LLM/search only manual smoke. |

## 13. Done criteria

Implementation is complete when:

- `baseline` command runs with real LLM.
- `multi-agent` command runs with real LangGraph workflow.
- Tavily search is used for Researcher.
- LLM-as-judge is used in benchmark.
- Local JSON traces are generated.
- Langfuse SDK v4 is used if Langfuse is enabled.
- `reports/benchmark_report.md` exists and contains required comparison.
- Tests pass.
- Lint/type checks pass or any remaining issues are documented.
- No hardcoded secrets exist.
- `docs/design_template.md` is filled.

## 14. Recommended final demo commands

```bash
python -m multi_agent_research_lab.cli --help

python -m multi_agent_research_lab.cli baseline \
  --query "Research GraphRAG state-of-the-art and write a 500-word summary"

python -m multi_agent_research_lab.cli multi-agent \
  --query "Research GraphRAG state-of-the-art and write a 500-word summary"

python -m multi_agent_research_lab.cli benchmark --output-dir reports
```

Quality gates:

```bash
pytest --cov=src --cov-report=term-missing
ruff check src tests
ruff format --check src tests
mypy src
```
