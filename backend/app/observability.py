from __future__ import annotations

import os
import threading
import time
from collections import defaultdict
from dataclasses import dataclass


@dataclass
class Alert:
    name: str
    severity: str
    message: str
    value: float
    threshold: float


class Telemetry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, float] = defaultdict(float)
        self._gauges: dict[str, float] = defaultdict(float)
        self._timers_sum_ms: dict[str, float] = defaultdict(float)
        self._timers_count: dict[str, int] = defaultdict(int)
        self._started_at = time.time()

    def incr(self, name: str, value: float = 1.0) -> None:
        with self._lock:
            self._counters[name] += value

    def set_gauge(self, name: str, value: float) -> None:
        with self._lock:
            self._gauges[name] = value

    def observe_ms(self, name: str, value_ms: float) -> None:
        with self._lock:
            self._timers_sum_ms[name] += value_ms
            self._timers_count[name] += 1

    def snapshot(self) -> dict:
        with self._lock:
            timers_avg_ms = {}
            for name, total in self._timers_sum_ms.items():
                count = self._timers_count[name]
                timers_avg_ms[name] = (total / count) if count else 0.0

            uptime = time.time() - self._started_at
            return {
                "uptime_seconds": uptime,
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "timers_avg_ms": timers_avg_ms,
            }

    def evaluate_alerts(self) -> list[dict]:
        snap = self.snapshot()
        alerts: list[Alert] = []

        terminal_failures = snap["counters"].get("worker.task_failed_terminal", 0.0)
        retries = snap["counters"].get("worker.task_retry_scheduled", 0.0)
        api_5xx = snap["counters"].get("api.requests.5xx", 0.0)

        terminal_failure_threshold = float(os.getenv("VT_ALERT_TERMINAL_FAILURES", "1"))
        retry_threshold = float(os.getenv("VT_ALERT_RETRIES", "5"))
        api_5xx_threshold = float(os.getenv("VT_ALERT_API_5XX", "1"))

        if terminal_failures >= terminal_failure_threshold:
            alerts.append(
                Alert(
                    name="terminal_failures",
                    severity="high",
                    message="Terminal worker failures reached threshold",
                    value=terminal_failures,
                    threshold=terminal_failure_threshold,
                )
            )
        if retries >= retry_threshold:
            alerts.append(
                Alert(
                    name="retry_spike",
                    severity="medium",
                    message="Worker retries reached threshold",
                    value=retries,
                    threshold=retry_threshold,
                )
            )
        if api_5xx >= api_5xx_threshold:
            alerts.append(
                Alert(
                    name="api_5xx",
                    severity="high",
                    message="API 5xx responses reached threshold",
                    value=api_5xx,
                    threshold=api_5xx_threshold,
                )
            )

        return [a.__dict__ for a in alerts]


telemetry = Telemetry()
