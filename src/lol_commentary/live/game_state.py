from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

import cv2
import numpy as np

from ..video.hud_regions import PlayerHUD, SpectatorHUD
from ..video.ocr_engine import OCREngine

logger = logging.getLogger(__name__)


@dataclass
class GameState:
    """Current game state extracted from HUD."""
    game_time: str | None = None  # "MM:SS"
    game_time_seconds: int = 0
    blue_score: int = 0
    red_score: int = 0
    game_phase: str = "early"  # "early" / "mid" / "late"

    def copy(self) -> GameState:
        return GameState(
            game_time=self.game_time,
            game_time_seconds=self.game_time_seconds,
            blue_score=self.blue_score,
            red_score=self.red_score,
            game_phase=self.game_phase,
        )


@dataclass
class StateChange:
    """A detected change in game state."""
    change_type: str  # "kill" / "phase_change"
    team: str | None  # "blue" / "red"
    old_value: Any
    new_value: Any
    timestamp: float


class FrameDiffChecker:
    """Check if HUD regions have changed using pixel-level MSE comparison.

    This avoids running OCR on every frame — only run OCR when pixels change.
    """

    def __init__(self, threshold: float = 30.0) -> None:
        self._threshold = threshold
        self._previous: dict[str, np.ndarray] = {}

    def has_changed(self, region_name: str, region_image: np.ndarray) -> bool:
        """Return True if the region has visually changed since last check."""
        gray = cv2.cvtColor(region_image, cv2.COLOR_BGR2GRAY) if len(region_image.shape) == 3 else region_image

        prev = self._previous.get(region_name)
        if prev is None:
            self._previous[region_name] = gray
            return True  # First frame — always process

        # Resize to match if needed
        if prev.shape != gray.shape:
            self._previous[region_name] = gray
            return True

        mse = np.mean((prev.astype(float) - gray.astype(float)) ** 2)
        if mse > self._threshold:
            self._previous[region_name] = gray
            return True

        return False


class GameStateTracker:
    """Track game state by running OCR on HUD regions that have changed.

    Auto-detects HUD layout (spectator vs player view) on the first few frames
    by trying both region sets and keeping whichever produces valid OCR results.
    """

    def __init__(self, ocr_engine: OCREngine, width: int, height: int) -> None:
        self._ocr = ocr_engine
        self._width = width
        self._height = height
        self._diff = FrameDiffChecker()
        self._state = GameState()

        # Start with both HUD layouts; auto-detect during first frames
        self._spectator_regions = SpectatorHUD.get_scaled_regions(width, height)
        self._player_regions = PlayerHUD.get_scaled_regions(width, height)
        self._regions = self._spectator_regions  # default
        self._hud_type: str | None = None  # None = not yet detected
        self._detect_attempts = 0
        self._detect_max = 30  # try for first 30 frames

    @property
    def state(self) -> GameState:
        return self._state

    def _try_detect_hud(self, frame: np.ndarray) -> None:
        """Try to auto-detect the HUD type by attempting OCR on both layouts."""
        self._detect_attempts += 1

        for name, regions in [("spectator", self._spectator_regions), ("player", self._player_regions)]:
            timer_region = regions["timer"]
            timer_crop = frame[timer_region.to_slice()]
            result = self._ocr.read_timer(timer_crop)
            if result is not None:
                self._hud_type = name
                self._regions = regions
                logger.info("HUD auto-detected: %s (timer=%s)", name, result)
                return

        if self._detect_attempts >= self._detect_max:
            # Default to player HUD if can't detect (more common for streams)
            self._hud_type = "player"
            self._regions = self._player_regions
            logger.info("HUD detection gave up after %d frames, defaulting to player HUD", self._detect_attempts)

    def update(self, frame: np.ndarray) -> list[StateChange]:
        """Process a frame and return any state changes detected."""
        # Auto-detect HUD layout if not yet determined
        if self._hud_type is None:
            self._try_detect_hud(frame)

        changes: list[StateChange] = []
        now = time.time()

        # Crop HUD regions
        timer_region = self._regions["timer"]
        blue_score_region = self._regions["blue_team_score"]
        red_score_region = self._regions["red_team_score"]

        timer_crop = frame[timer_region.to_slice()]
        blue_score_crop = frame[blue_score_region.to_slice()]
        red_score_crop = frame[red_score_region.to_slice()]

        # Timer
        if self._diff.has_changed("timer", timer_crop):
            game_time = self._ocr.read_timer(timer_crop)
            if game_time and game_time != self._state.game_time:
                self._state.game_time = game_time
                # Parse seconds
                parts = game_time.split(":")
                if len(parts) == 2:
                    try:
                        seconds = int(parts[0]) * 60 + int(parts[1])
                        self._state.game_time_seconds = seconds
                        # Update game phase
                        old_phase = self._state.game_phase
                        if seconds < 15 * 60:
                            self._state.game_phase = "early"
                        elif seconds < 25 * 60:
                            self._state.game_phase = "mid"
                        else:
                            self._state.game_phase = "late"
                        if self._state.game_phase != old_phase:
                            changes.append(StateChange(
                                change_type="phase_change",
                                team=None,
                                old_value=old_phase,
                                new_value=self._state.game_phase,
                                timestamp=now,
                            ))
                    except ValueError:
                        pass

        # Blue score
        if self._diff.has_changed("blue_score", blue_score_crop):
            score = self._ocr.read_score(blue_score_crop)
            if score is not None and score != self._state.blue_score:
                old = self._state.blue_score
                if score > old:
                    changes.append(StateChange(
                        change_type="kill",
                        team="blue",
                        old_value=old,
                        new_value=score,
                        timestamp=now,
                    ))
                self._state.blue_score = score

        # Red score
        if self._diff.has_changed("red_score", red_score_crop):
            score = self._ocr.read_score(red_score_crop)
            if score is not None and score != self._state.red_score:
                old = self._state.red_score
                if score > old:
                    changes.append(StateChange(
                        change_type="kill",
                        team="red",
                        old_value=old,
                        new_value=score,
                        timestamp=now,
                    ))
                self._state.red_score = score

        return changes
