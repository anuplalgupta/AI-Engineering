"""The one clock (ADR 0006 item 25).

No other file may ask the operating system for the time; a test enforces it.
"""

from datetime import UTC, datetime, timedelta
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime:
        """Current time, always timezone-aware UTC."""
        ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class FixedClock:
    """A clock that only moves when told to. For tests and simulations."""

    def __init__(self, start: datetime | None = None) -> None:
        self._now = start or datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
        if self._now.tzinfo is None:
            raise ValueError("FixedClock needs a timezone-aware time")

    def now(self) -> datetime:
        return self._now

    def set(self, moment: datetime) -> None:
        self._now = moment

    def advance(self, delta: timedelta | None = None, **kwargs: float) -> None:
        self._now += delta if delta is not None else timedelta(**kwargs)


_clock: Clock = SystemClock()


def get_clock() -> Clock:
    return _clock


def set_clock(clock: Clock) -> None:
    global _clock
    _clock = clock


def now() -> datetime:
    return _clock.now()
