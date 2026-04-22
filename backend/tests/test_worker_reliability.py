from __future__ import annotations

import unittest

from backend.app.models import Job, JobStatus
from backend.app.queue import InMemoryTaskQueue, make_queue_message
from backend.app.repository import InMemoryRepository
from backend.app.worker_runner import process_message_once


class _AlwaysFailWorker:
    def process_clip_1_generation(self, message) -> None:  # noqa: ANN001
        raise RuntimeError(f"forced failure for {message.job_id}")


class WorkerReliabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = InMemoryRepository()
        self.queue = InMemoryTaskQueue()
        self.worker = _AlwaysFailWorker()
        self.job = Job(client_slug="c1", format_seconds=20, clip_total=2)
        self.repo.create_job(self.job)

    def test_retry_is_scheduled_before_max_attempts(self) -> None:
        message = make_queue_message(
            job_id=self.job.id,
            task_type="generate_clip_1",
            task_key=f"{self.job.id}:clip_1_generation",
            trace_id="trace-retry-1",
            attempt=1,
            max_attempts=3,
        )

        process_message_once(
            worker=self.worker,
            store=self.repo,
            queue=self.queue,
            message=message,
            retry_base_seconds=2,
        )

        self.assertEqual(len(self.queue._delayed), 1)
        delayed_msg = self.queue._delayed[0][1]
        self.assertEqual(delayed_msg.attempt, 2)
        self.assertEqual(len(self.queue._dead_letter), 0)

        event_types = [event.event_type for event in self.repo.list_events(self.job.id)]
        self.assertIn("task_retry_scheduled", event_types)

    def test_dead_letter_and_job_failed_on_terminal_attempt(self) -> None:
        message = make_queue_message(
            job_id=self.job.id,
            task_type="generate_clip_1",
            task_key=f"{self.job.id}:clip_1_generation",
            trace_id="trace-terminal-1",
            attempt=3,
            max_attempts=3,
        )

        process_message_once(
            worker=self.worker,
            store=self.repo,
            queue=self.queue,
            message=message,
            retry_base_seconds=2,
        )

        self.assertEqual(len(self.queue._delayed), 0)
        self.assertEqual(len(self.queue._dead_letter), 1)

        saved = self.repo.get_job(self.job.id)
        self.assertIsNotNone(saved)
        self.assertEqual(saved.status, JobStatus.FAILED)

        event_types = [event.event_type for event in self.repo.list_events(self.job.id)]
        self.assertIn("task_failed_terminal", event_types)
        self.assertIn("job_failed", event_types)


if __name__ == "__main__":
    unittest.main()
