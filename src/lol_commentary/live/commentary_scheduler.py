"""Commentary scheduling with pacing control and fill generation."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from .event_detector import LiveEvent
from .game_state import GameState


@dataclass
class ScheduledComment:
    """A commentary item queued for delivery."""
    event: LiveEvent | None
    game_time: str
    priority: float  # Higher = more important
    comment_type: str  # "event" or "fill"
    deliver_after: float  # Unix timestamp after which this can be delivered

    @property
    def is_ready(self) -> bool:
        return time.time() >= self.deliver_after


class CommentaryScheduler:
    """Controls pacing of commentary to avoid overwhelming the viewer.

    - Enforces minimum interval between comments
    - High-significance events bypass the interval
    - Generates fill requests during quiet periods
    """

    IMMEDIATE_THRESHOLD = 0.7  # significance >= this delivers immediately

    def __init__(
        self,
        min_interval: float = 8.0,
        fill_interval: float = 30.0,
    ) -> None:
        self._min_interval = min_interval
        self._fill_interval = fill_interval
        self._queue: list[ScheduledComment] = []
        self._last_delivery: float = 0.0
        self._last_event_time: float = time.time()

    def enqueue(self, event: LiveEvent, state: GameState) -> None:
        """Add an event to the commentary queue with pacing control."""
        now = time.time()
        self._last_event_time = now

        if event.significance >= self.IMMEDIATE_THRESHOLD:
            # High-significance: deliver immediately
            deliver_after = now
        else:
            # Ensure minimum interval from last delivery
            deliver_after = max(now, self._last_delivery + self._min_interval)

        comment = ScheduledComment(
            event=event,
            game_time=event.game_time,
            priority=event.significance,
            comment_type="event",
            deliver_after=deliver_after,
        )

        # Insert in priority order (higher priority first among same-time items)
        self._queue.append(comment)
        self._queue.sort(key=lambda c: (-c.priority, c.deliver_after))

    def next_ready(self) -> ScheduledComment | None:
        """Return the next comment ready for delivery, or None."""
        for i, comment in enumerate(self._queue):
            if comment.is_ready:
                self._queue.pop(i)
                self._last_delivery = time.time()
                return comment
        return None

    def should_fill(self) -> bool:
        """Return True if enough time has passed without events to warrant a fill comment."""
        elapsed = time.time() - self._last_event_time
        time_since_delivery = time.time() - self._last_delivery
        return (
            elapsed >= self._fill_interval
            and time_since_delivery >= self._min_interval
            and not self._queue  # Don't fill if events are queued
        )

    def create_fill_request(self, state: GameState) -> ScheduledComment:
        """Create a fill comment request for quiet periods."""
        now = time.time()
        self._last_event_time = now  # Reset fill timer

        return ScheduledComment(
            event=None,
            game_time=state.game_time or "??:??",
            priority=0.1,
            comment_type="fill",
            deliver_after=now,
        )

    @property
    def queue_size(self) -> int:
        return len(self._queue)

    def clear(self) -> None:
        """Clear the queue."""
        self._queue.clear()
