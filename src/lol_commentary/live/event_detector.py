from __future__ import annotations

import logging
from dataclasses import dataclass, field

from .game_state import GameState, StateChange

logger = logging.getLogger(__name__)


@dataclass
class LiveEvent:
    """A game event detected from state changes."""
    timestamp: float
    game_time: str
    event_type: str  # "kill" / "multi_kill" / "teamfight" / "phase_change"
    team: str | None
    description: str  # Basic Japanese description
    significance: float  # 0.0-1.0


class LiveEventDetector:
    """Convert state changes into game events with significance scoring."""

    TEAMFIGHT_WINDOW = 15.0  # seconds
    TEAMFIGHT_MIN_KILLS = 3

    def __init__(self) -> None:
        self._recent_kills: list[StateChange] = []

    def detect(self, changes: list[StateChange], state: GameState) -> list[LiveEvent]:
        """Detect events from state changes, applying significance scoring."""
        events: list[LiveEvent] = []
        game_time = state.game_time or "??:??"

        for change in changes:
            if change.change_type == "kill":
                self._recent_kills.append(change)
                events.append(self._handle_kill(change, state, game_time))

            elif change.change_type == "phase_change":
                events.append(LiveEvent(
                    timestamp=change.timestamp,
                    game_time=game_time,
                    event_type="phase_change",
                    team=None,
                    description=f"ゲームフェーズが{_phase_name(change.new_value)}に移行",
                    significance=0.4,
                ))

        # Check for teamfight (multiple kills in short window)
        teamfight_event = self._check_teamfight(state, game_time)
        if teamfight_event:
            events.append(teamfight_event)

        # Prune old kills
        if self._recent_kills:
            cutoff = self._recent_kills[-1].timestamp - self.TEAMFIGHT_WINDOW
            self._recent_kills = [k for k in self._recent_kills if k.timestamp >= cutoff]

        return events

    def _handle_kill(self, change: StateChange, state: GameState, game_time: str) -> LiveEvent:
        """Create an event for a single kill."""
        team_name = "ブルー" if change.team == "blue" else "レッド"
        kills_gained = change.new_value - change.old_value
        total_score = f"{state.blue_score}-{state.red_score}"

        # Significance based on game phase and score state
        base_sig = 0.4
        if state.game_phase == "early":
            base_sig = 0.5  # Early kills are more impactful
        elif state.game_phase == "late":
            base_sig = 0.45

        # Multi-kill bonus
        if kills_gained > 1:
            base_sig = min(1.0, base_sig + kills_gained * 0.1)
            description = f"{team_name}側が{kills_gained}キルを獲得！ (スコア: {total_score})"
        else:
            description = f"{team_name}側がキルを獲得 (スコア: {total_score})"

        return LiveEvent(
            timestamp=change.timestamp,
            game_time=game_time,
            event_type="kill" if kills_gained == 1 else "multi_kill",
            team=change.team,
            description=description,
            significance=min(1.0, base_sig),
        )

    def _check_teamfight(self, state: GameState, game_time: str) -> LiveEvent | None:
        """Check if recent kills constitute a teamfight."""
        if len(self._recent_kills) < self.TEAMFIGHT_MIN_KILLS:
            return None

        window = self._recent_kills[-1].timestamp - self._recent_kills[0].timestamp
        if window > self.TEAMFIGHT_WINDOW:
            return None

        # Count kills per team in this window
        blue_kills = sum(1 for k in self._recent_kills if k.team == "blue")
        red_kills = sum(1 for k in self._recent_kills if k.team == "red")
        total = blue_kills + red_kills

        if total < self.TEAMFIGHT_MIN_KILLS:
            return None

        winner = "ブルー" if blue_kills > red_kills else "レッド" if red_kills > blue_kills else None
        if winner:
            description = f"集団戦発生！ {winner}側が{blue_kills}-{red_kills}で勝利 (スコア: {state.blue_score}-{state.red_score})"
        else:
            description = f"集団戦発生！ {blue_kills}-{red_kills}の相打ち (スコア: {state.blue_score}-{state.red_score})"

        # Capture timestamp before clearing
        event_timestamp = self._recent_kills[-1].timestamp

        # Clear recent kills to avoid duplicate detection
        self._recent_kills.clear()

        return LiveEvent(
            timestamp=event_timestamp,
            game_time=game_time,
            event_type="teamfight",
            team=None,
            description=description,
            significance=0.8,
        )


def _phase_name(phase: str) -> str:
    return {"early": "序盤", "mid": "中盤", "late": "終盤"}.get(phase, phase)
