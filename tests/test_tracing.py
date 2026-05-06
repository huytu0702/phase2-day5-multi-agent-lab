import pytest

from multi_agent_research_lab.observability.tracing import trace_span


def test_trace_span_records_duration_and_name() -> None:
    with trace_span("unit.test", {"key": "value"}) as span:
        span["attributes"]["extra"] = "ok"

    assert span["name"] == "unit.test"
    assert span["attributes"]["key"] == "value"
    assert span["attributes"]["extra"] == "ok"
    assert isinstance(span["duration_seconds"], float)
    assert span["duration_seconds"] >= 0.0
    assert span["status"] == "ok"


def test_trace_span_marks_error_status() -> None:
    with pytest.raises(ValueError):
        with trace_span("unit.error") as span:
            raise ValueError("boom")

    assert span["status"] == "error"
    assert span["attributes"]["error_type"] == "ValueError"
    assert span["attributes"]["error_message"] == "boom"
