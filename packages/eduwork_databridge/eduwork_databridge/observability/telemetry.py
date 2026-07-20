from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.trace import TracerProvider

SENSITIVE_TOKENS = {"secret", "token", "password", "raw", "record", "email", "name"}


def sanitize_attributes(attributes: dict[str, Any]) -> dict[str, str | int | float | bool]:
    safe: dict[str, str | int | float | bool] = {}
    for key, value in attributes.items():
        lowered = key.casefold()
        if any(token in lowered for token in SENSITIVE_TOKENS):
            continue
        if isinstance(value, str | int | float | bool):
            safe[key] = value[:200] if isinstance(value, str) else value
    return safe


class Telemetry:
    def __init__(self, service_name: str = "eduwork-databridge") -> None:
        self.trace_provider = TracerProvider()
        self.meter_provider = MeterProvider()
        self.tracer = self.trace_provider.get_tracer(service_name)
        self.meter = self.meter_provider.get_meter(service_name)
        self.run_counter = self.meter.create_counter("eduwork.asset_runs")
        self.duration_histogram = self.meter.create_histogram("eduwork.asset_duration_ms")
        self.events: list[dict[str, Any]] = []

    @contextmanager
    def span(self, name: str, attributes: dict[str, Any]) -> Iterator[None]:
        safe = sanitize_attributes(attributes)
        with self.tracer.start_as_current_span(name, attributes=safe):
            self.events.append({"name": name, "attributes": safe})
            yield

    def record_run(self, status: str, duration_ms: float, attributes: dict[str, Any]) -> None:
        safe = sanitize_attributes(attributes)
        measurements = {**safe, "status": status}
        self.run_counter.add(1, measurements)
        self.duration_histogram.record(duration_ms, measurements)
        self.events.append(
            {
                "name": "asset_run_metric",
                "attributes": measurements,
                "duration_ms": round(duration_ms, 3),
            }
        )
