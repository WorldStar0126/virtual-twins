from __future__ import annotations

import json
import os
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import uuid4


@dataclass
class QueueMessage:
    message_id: str
    job_id: str
    task_type: str
    task_key: str
    trace_id: str
    attempt: int = 1
    max_attempts: int = 3


class TaskQueue(Protocol):
    def enqueue(self, message: QueueMessage, delay_seconds: int = 0) -> None: ...
    def dequeue(self, timeout_seconds: int = 5) -> QueueMessage | None: ...
    def enqueue_dead_letter(self, message: QueueMessage, reason: str) -> None: ...


class InMemoryTaskQueue:
    def __init__(self) -> None:
        self._queue: deque[QueueMessage] = deque()
        self._delayed: list[tuple[float, QueueMessage]] = []
        self._dead_letter: list[dict[str, Any]] = []

    def enqueue(self, message: QueueMessage, delay_seconds: int = 0) -> None:
        if delay_seconds > 0:
            available_at = time.time() + delay_seconds
            self._delayed.append((available_at, message))
            return
        self._queue.append(message)

    def dequeue(self, timeout_seconds: int = 5) -> QueueMessage | None:
        _ = timeout_seconds
        now = time.time()
        ready: list[tuple[float, QueueMessage]] = []
        waiting: list[tuple[float, QueueMessage]] = []
        for available_at, message in self._delayed:
            if available_at <= now:
                ready.append((available_at, message))
            else:
                waiting.append((available_at, message))
        self._delayed = waiting
        for _, message in sorted(ready, key=lambda item: item[0]):
            self._queue.append(message)

        if not self._queue:
            return None
        return self._queue.popleft()

    def enqueue_dead_letter(self, message: QueueMessage, reason: str) -> None:
        self._dead_letter.append(
            {
                "message": message,
                "reason": reason,
                "failed_at_epoch": time.time(),
            }
        )


class RedisTaskQueue:
    def __init__(self, redis_url: str, queue_name: str = "vt:jobs") -> None:
        import redis  # local import to keep in-memory mode dependency-light

        self._client = redis.from_url(redis_url, decode_responses=True)
        self._queue_name = queue_name
        self._delayed_queue_name = f"{queue_name}:delayed"
        self._dead_letter_queue_name = f"{queue_name}:dlq"

    def enqueue(self, message: QueueMessage, delay_seconds: int = 0) -> None:
        payload = json.dumps(
            {
                "message_id": message.message_id,
                "job_id": message.job_id,
                "task_type": message.task_type,
                "task_key": message.task_key,
                "trace_id": message.trace_id,
                "attempt": message.attempt,
                "max_attempts": message.max_attempts,
            }
        )
        if delay_seconds > 0:
            available_at = time.time() + delay_seconds
            self._client.zadd(self._delayed_queue_name, {payload: available_at})
            return
        self._client.rpush(self._queue_name, payload)

    def dequeue(self, timeout_seconds: int = 5) -> QueueMessage | None:
        now = time.time()
        due = self._client.zrangebyscore(self._delayed_queue_name, min=0, max=now)
        if due:
            pipe = self._client.pipeline()
            for payload in due:
                pipe.rpush(self._queue_name, payload)
                pipe.zrem(self._delayed_queue_name, payload)
            pipe.execute()

        result = self._client.blpop(self._queue_name, timeout=timeout_seconds)
        if not result:
            return None
        _queue_name, payload = result
        data = json.loads(payload)
        return QueueMessage(
            message_id=data["message_id"],
            job_id=data["job_id"],
            task_type=data["task_type"],
            task_key=data["task_key"],
            trace_id=data["trace_id"],
            attempt=data.get("attempt", 1),
            max_attempts=data.get("max_attempts", 3),
        )

    def enqueue_dead_letter(self, message: QueueMessage, reason: str) -> None:
        payload = json.dumps(
            {
                "message_id": message.message_id,
                "job_id": message.job_id,
                "task_type": message.task_type,
                "task_key": message.task_key,
                "trace_id": message.trace_id,
                "attempt": message.attempt,
                "max_attempts": message.max_attempts,
                "reason": reason,
                "failed_at_epoch": time.time(),
            }
        )
        self._client.rpush(self._dead_letter_queue_name, payload)


def build_task_queue() -> TaskQueue:
    backend = os.getenv("VT_QUEUE_BACKEND", "memory").strip().lower()
    if backend == "redis":
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        return RedisTaskQueue(redis_url=redis_url)
    return InMemoryTaskQueue()


def make_queue_message(
    job_id: str,
    task_type: str,
    task_key: str,
    trace_id: str,
    attempt: int = 1,
    max_attempts: int = 3,
) -> QueueMessage:
    return QueueMessage(
        message_id=str(uuid4()),
        job_id=job_id,
        task_type=task_type,
        task_key=task_key,
        trace_id=trace_id,
        attempt=attempt,
        max_attempts=max_attempts,
    )
