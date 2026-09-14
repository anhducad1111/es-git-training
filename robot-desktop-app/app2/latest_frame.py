from __future__ import annotations

from threading import Condition
from time import monotonic
from typing import Generic, TypeVar

T = TypeVar("T")


class LatestFrame(Generic[T]):
    """A capacity-one, thread-safe handoff that always keeps the newest item."""

    def __init__(self) -> None:
        self._condition = Condition()
        self._value: T | None = None
        self._closed = False

    def put(self, value: T) -> None:
        with self._condition:
            if self._closed:
                return
            self._value = value
            self._condition.notify()

    def get(self, timeout: float | None = None) -> T | None:
        with self._condition:
            deadline = None if timeout is None else monotonic() + timeout
            while self._value is None and not self._closed:
                remaining = None if deadline is None else deadline - monotonic()
                if remaining is not None and remaining <= 0:
                    return None
                self._condition.wait(remaining)
            value, self._value = self._value, None
            return value

    def close(self) -> None:
        with self._condition:
            self._closed = True
            self._value = None
            self._condition.notify_all()

    @property
    def closed(self) -> bool:
        with self._condition:
            return self._closed
