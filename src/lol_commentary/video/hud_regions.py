from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Region:
    """A rectangular region on the screen."""
    x: int
    y: int
    width: int
    height: int

    def scale(self, scale_x: float, scale_y: float) -> Region:
        return Region(
            x=int(self.x * scale_x),
            y=int(self.y * scale_y),
            width=int(self.width * scale_x),
            height=int(self.height * scale_y),
        )

    def to_slice(self) -> tuple[slice, slice]:
        """Return (y_slice, x_slice) for numpy/OpenCV array indexing."""
        return (
            slice(self.y, self.y + self.height),
            slice(self.x, self.x + self.width),
        )


class SpectatorHUD:
    """HUD region definitions for LoL spectator mode at 1080p (1920x1080).

    These coordinates are approximate and may need adjustment for
    different game patches or spectator client versions.
    """
    BASE_WIDTH = 1920
    BASE_HEIGHT = 1080

    # Game timer (top center)
    TIMER = Region(x=920, y=8, width=80, height=30)

    # Blue team name (top left area)
    BLUE_TEAM_NAME = Region(x=340, y=8, width=200, height=28)

    # Red team name (top right area)
    RED_TEAM_NAME = Region(x=1380, y=8, width=200, height=28)

    # Blue team score/kills (top left)
    BLUE_TEAM_SCORE = Region(x=860, y=8, width=50, height=28)

    # Red team score/kills (top right)
    RED_TEAM_SCORE = Region(x=1010, y=8, width=50, height=28)

    # Gold display (top center, below timer)
    BLUE_TEAM_GOLD = Region(x=780, y=38, width=120, height=24)
    RED_TEAM_GOLD = Region(x=1020, y=38, width=120, height=24)

    # Scoreboard player names (left side, blue team)
    BLUE_PLAYER_NAMES = [
        Region(x=10, y=70 + i * 32, width=140, height=28) for i in range(5)
    ]

    # Scoreboard player names (right side, red team)
    RED_PLAYER_NAMES = [
        Region(x=1770, y=70 + i * 32, width=140, height=28) for i in range(5)
    ]

    # Kill feed (top right corner)
    KILL_FEED = Region(x=1500, y=70, width=400, height=200)

    # Minimap (bottom right)
    MINIMAP = Region(x=1630, y=790, width=280, height=280)

    # All player name regions combined
    ALL_PLAYER_NAMES = BLUE_PLAYER_NAMES + RED_PLAYER_NAMES

    @classmethod
    def get_scaled_regions(cls, width: int, height: int) -> dict[str, Region | list[Region]]:
        """Get all HUD regions scaled to the given resolution."""
        scale_x = width / cls.BASE_WIDTH
        scale_y = height / cls.BASE_HEIGHT
        return {
            "timer": cls.TIMER.scale(scale_x, scale_y),
            "blue_team_name": cls.BLUE_TEAM_NAME.scale(scale_x, scale_y),
            "red_team_name": cls.RED_TEAM_NAME.scale(scale_x, scale_y),
            "blue_team_score": cls.BLUE_TEAM_SCORE.scale(scale_x, scale_y),
            "red_team_score": cls.RED_TEAM_SCORE.scale(scale_x, scale_y),
            "blue_team_gold": cls.BLUE_TEAM_GOLD.scale(scale_x, scale_y),
            "red_team_gold": cls.RED_TEAM_GOLD.scale(scale_x, scale_y),
            "blue_player_names": [r.scale(scale_x, scale_y) for r in cls.BLUE_PLAYER_NAMES],
            "red_player_names": [r.scale(scale_x, scale_y) for r in cls.RED_PLAYER_NAMES],
            "kill_feed": cls.KILL_FEED.scale(scale_x, scale_y),
            "minimap": cls.MINIMAP.scale(scale_x, scale_y),
        }
