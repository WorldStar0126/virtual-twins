from __future__ import annotations

import os
import unittest

from backend.app.observability import Telemetry


class ObservabilityTests(unittest.TestCase):
    def test_alerts_trigger_when_thresholds_crossed(self) -> None:
        os.environ["VT_ALERT_TERMINAL_FAILURES"] = "1"
        os.environ["VT_ALERT_RETRIES"] = "2"
        os.environ["VT_ALERT_API_5XX"] = "1"

        t = Telemetry()
        t.incr("worker.task_failed_terminal", 1)
        t.incr("worker.task_retry_scheduled", 2)
        t.incr("api.requests.5xx", 1)

        alerts = t.evaluate_alerts()
        names = {a["name"] for a in alerts}
        self.assertIn("terminal_failures", names)
        self.assertIn("retry_spike", names)
        self.assertIn("api_5xx", names)

    def test_snapshot_includes_timer_averages(self) -> None:
        t = Telemetry()
        t.observe_ms("api.requests.latency", 100)
        t.observe_ms("api.requests.latency", 200)
        snap = t.snapshot()
        self.assertEqual(snap["timers_avg_ms"]["api.requests.latency"], 150)


if __name__ == "__main__":
    unittest.main()
