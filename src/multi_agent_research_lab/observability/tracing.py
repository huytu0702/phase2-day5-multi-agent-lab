"""Provider-agnostic tracing utilities with local JSON persistence."""

from __future__ import annotations

import json
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

from multi_agent_research_lab.core.config import get_settings


def _copy_attributes(attributes: dict[str, Any] | None) -> dict[str, Any]:
    return dict(attributes or {})


_TRACE_CONTEXT: ContextVar[Any | None] = ContextVar("trace_context", default=None)


class _LangfuseV4Adapter:
    """Optional Langfuse adapter enabled by environment."""

    def __init__(self) -> None:
        self._client: Any | None = None
        settings = get_settings()
        if not settings.langfuse_v4_enabled:
            return
        if not settings.langfuse_public_key or not settings.langfuse_secret_key:
            return
        try:
            from langfuse import Langfuse  # type: ignore

            host = settings.langfuse_host or settings.langfuse_base_url
            if host:
                self._client = Langfuse(
                    host=host,
                    public_key=settings.langfuse_public_key,
                    secret_key=settings.langfuse_secret_key,
                )
            else:
                self._client = Langfuse(
                    public_key=settings.langfuse_public_key,
                    secret_key=settings.langfuse_secret_key,
                )
        except Exception:
            self._client = None

    def begin_trace(self, name: str, metadata: dict[str, Any] | None = None) -> Any | None:
        if self._client is None:
            return None
        try:
            trace_context = {"trace_id": self._client.create_trace_id()}
            self._client.create_event(
                name=name,
                trace_context=trace_context,
                metadata=metadata or {"kind": "run_start"},
            )
            self._client.flush()
            return trace_context
        except Exception:
            return None

    def emit(self, event: dict[str, Any], trace_context: Any | None = None) -> None:
        if self._client is None:
            return
        try:
            self._client.create_event(
                name=str(event.get("name", "span")),
                trace_context=trace_context or _TRACE_CONTEXT.get(),
                input=event.get("input", event.get("attributes")),
                output=event.get("output"),
                metadata=event,
            )
            self._client.flush()
        except Exception:
            return


class TraceRecorder:
    """Always-on local JSONL tracer with optional Langfuse forwarding."""

    def __init__(self, trace_file: str | Path | None = None) -> None:
        output = Path(trace_file) if trace_file is not None else Path("traces") / "local_trace.jsonl"
        output.parent.mkdir(parents=True, exist_ok=True)
        self.trace_path = output
        self._langfuse = _LangfuseV4Adapter()

    def record(self, event: dict[str, Any], trace_context: Any | None = None) -> None:
        payload = {"timestamp": datetime.now(UTC).isoformat(), **event}
        with self.trace_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        self._langfuse.emit(payload, trace_context=trace_context)


_DEFAULT_RECORDER = TraceRecorder()


@contextmanager
def trace_span(
    name: str,
    attributes: dict[str, Any] | None = None,
    trace_context: Any | None = None,
) -> Iterator[dict[str, Any]]:
    """Capture span metadata and elapsed time and persist to local JSON."""

    started = perf_counter()
    span: dict[str, Any] = {
        "name": name,
        "attributes": _copy_attributes(attributes),
        "input": None,
        "output": None,
        "duration_seconds": None,
        "status": "ok",
    }
    try:
        yield span
    except Exception as exc:
        span["status"] = "error"
        span["attributes"]["error_type"] = exc.__class__.__name__
        span["attributes"]["error_message"] = str(exc)
        raise
    finally:
        span["duration_seconds"] = perf_counter() - started
        _DEFAULT_RECORDER.record(span, trace_context=trace_context)


@contextmanager
def trace_run(name: str, metadata: dict[str, Any] | None = None) -> Iterator[Any | None]:
    """Bind a single trace context for an end-to-end runtime execution."""

    trace_context = _DEFAULT_RECORDER._langfuse.begin_trace(name=name, metadata=metadata)
    token = _TRACE_CONTEXT.set(trace_context)
    try:
        yield trace_context
    finally:
        _TRACE_CONTEXT.reset(token)
