"""Tests for the commentary scheduler."""

import time

import pytest

from lol_commentary.live.commentary_scheduler import (
    CommentaryScheduler,
    ScheduledComment,
)
from lol_commentary.live.event_detector import LiveEvent
from lol_commentary.live.game_state import GameState


def _make_event(significance: float = 0.5, game_time: str = "10:00") -> LiveEvent:
    return LiveEvent(
        timestamp=time.time(),
        game_time=game_time,
        event_type="kill",
        team="blue",
        description="テストイベント",
        significance=significance,
    )


def _make_state() -> GameState:
    return GameState(
        game_time="10:00",
        game_time_seconds=600,
        blue_score=3,
        red_score=2,
        game_phase="mid",
    )


class TestScheduledComment:
    def test_is_ready_past_time(self):
        comment = ScheduledComment(
            event=None,
            game_time="10:00",
            priority=0.5,
            comment_type="event",
            deliver_after=time.time() - 1,
        )
        assert comment.is_ready is True

    def test_is_ready_future_time(self):
        comment = ScheduledComment(
            event=None,
            game_time="10:00",
            priority=0.5,
            comment_type="event",
            deliver_after=time.time() + 100,
        )
        assert comment.is_ready is False


class TestCommentaryScheduler:
    def test_enqueue_high_significance_immediate(self):
        scheduler = CommentaryScheduler(min_interval=8.0)
        event = _make_event(significance=0.8)
        state = _make_state()

        scheduler.enqueue(event, state)
        ready = scheduler.next_ready()

        assert ready is not None
        assert ready.event is event
        assert ready.comment_type == "event"

    def test_enqueue_low_significance_respects_interval(self):
        scheduler = CommentaryScheduler(min_interval=8.0)
        # Simulate a recent delivery
        scheduler._last_delivery = time.time()

        event = _make_event(significance=0.4)
        state = _make_state()
        scheduler.enqueue(event, state)

        # Should not be ready yet (within min_interval)
        ready = scheduler.next_ready()
        assert ready is None

    def test_next_ready_returns_highest_priority_first(self):
        scheduler = CommentaryScheduler(min_interval=0.0)

        e1 = _make_event(significance=0.4)
        e2 = _make_event(significance=0.9)

        state = _make_state()
        scheduler.enqueue(e1, state)
        scheduler.enqueue(e2, state)

        ready = scheduler.next_ready()
        assert ready is not None
        assert ready.event is e2

    def test_next_ready_returns_none_when_empty(self):
        scheduler = CommentaryScheduler()
        assert scheduler.next_ready() is None

    def test_should_fill_after_interval(self):
        scheduler = CommentaryScheduler(fill_interval=0.01, min_interval=0.0)
        scheduler._last_event_time = time.time() - 1.0
        scheduler._last_delivery = time.time() - 1.0

        assert scheduler.should_fill() is True

    def test_should_fill_false_when_events_recent(self):
        scheduler = CommentaryScheduler(fill_interval=30.0)
        # Event just happened
        scheduler._last_event_time = time.time()
        assert scheduler.should_fill() is False

    def test_should_fill_false_when_queue_has_items(self):
        scheduler = CommentaryScheduler(fill_interval=0.01, min_interval=0.0)
        scheduler._last_event_time = time.time() - 1.0
        scheduler._last_delivery = time.time() - 1.0

        event = _make_event(significance=0.5)
        state = _make_state()
        scheduler.enqueue(event, state)

        assert scheduler.should_fill() is False

    def test_create_fill_request(self):
        scheduler = CommentaryScheduler()
        state = _make_state()

        fill = scheduler.create_fill_request(state)
        assert fill.comment_type == "fill"
        assert fill.event is None
        assert fill.game_time == "10:00"

    def test_queue_size(self):
        scheduler = CommentaryScheduler(min_interval=100.0)
        state = _make_state()

        assert scheduler.queue_size == 0
        scheduler.enqueue(_make_event(significance=0.4), state)
        assert scheduler.queue_size == 1

    def test_clear(self):
        scheduler = CommentaryScheduler(min_interval=100.0)
        state = _make_state()

        scheduler.enqueue(_make_event(significance=0.4), state)
        scheduler.clear()
        assert scheduler.queue_size == 0
