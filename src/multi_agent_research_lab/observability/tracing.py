"""Provider-agnostic tracing utilities with local JSON persistence."""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any


def _copy_attributes(attributes: dict[str, Any] | None) -> dict[str, Any]:
    return dict(attributes or {})


class _LangfuseV4Adapter:
    """Optional Langfuse v4 adapter."""

    def __init__(self) -> None:
        self._client: Any | None = None
        if os.getenv("LANGFUSE_V4_ENABLED", "false").lower() != "true":
            return
        try:
            from langfuse import Langfuse  # type: ignore

            self._client = Langfuse()
        except Exception:
            self._client = None

    def emit(self, event: dict[str, Any]) -> None:
        if self._client is None:
            return
        try:
            self._client.trace(name=event.get("name", "span"), metadata=event)
        except Exception:
            return


class TraceRecorder:
    """Always-on local JSONL tracer with optional Langfuse forwarding."""

    def __init__(self, trace_file: str | Path | None = None) -> None:
        output = Path(trace_file) if trace_file is not None else Path("traces") / "local_trace.jsonl"
        output.parent.mkdir(parents=True, exist_ok=True)
        self.trace_path = output
        self._langfuse = _LangfuseV4Adapter()

    def record(self, event: dict[str, Any]) -> None:
        payload = {"timestamp": datetime.now(UTC).isoformat(), **event}
        with self.trace_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        self._langfuse.emit(payload)


_DEFAULT_RECORDER = TraceRecorder()


@contextmanager
def trace_span(name: str, attributes: dict[str, Any] | None = None) -> Iterator[dict[str, Any]]:
    """Capture span metadata and elapsed time and persist to local JSON."""

    started = perf_counter()
    span: dict[str, Any] = {
        "name": name,
        "attributes": _copy_attributes(attributes),
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
        _DEFAULT_RECORDER.record(span)
