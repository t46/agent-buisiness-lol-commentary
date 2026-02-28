from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class SegmentContext:
    """Context data for a game segment."""
    video_time: str  # MM:SS format
    game_time: str  # MM:SS format
    events: list[dict] = field(default_factory=list)
    team_gold: dict[str, int] = field(default_factory=dict)  # blue/red -> gold
    objectives_state: dict[str, list] = field(default_factory=dict)  # dragons, barons, etc.
    active_buffs: list[str] = field(default_factory=list)
    gold_diff: int = 0
    kills_blue: int = 0
    kills_red: int = 0


@dataclass
class CommentaryEntry:
    """A single commentary message."""
    video_time: str  # MM:SS format
    game_time: str  # MM:SS format
    type: str  # "player", "team", "overall"
    message: str
    significance: float  # 0.0 to 1.0

    def to_dict(self) -> dict:
        return {
            "video_time": self.video_time,
            "game_time": self.game_time,
            "type": self.type,
            "message": self.message,
            "significance": round(self.significance, 2),
        }


@dataclass
class GameContext:
    """Overall game context for commentary generation."""
    match_id: str = ""
    patch: str = ""
    duration: str = ""  # MM:SS format
    blue_team: list[str] = field(default_factory=list)
    red_team: list[str] = field(default_factory=list)
    blue_champions: list[str] = field(default_factory=list)
    red_champions: list[str] = field(default_factory=list)
    draft_analysis: str = ""
    winner: str = ""  # "blue" or "red"


@dataclass
class CommentaryOutput:
    """Complete commentary output for a game."""
    game_info: GameContext
    commentary: list[CommentaryEntry] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "game_info": {
                "match_id": self.game_info.match_id,
                "patch": self.game_info.patch,
                "duration": self.game_info.duration,
                "blue_team": self.game_info.blue_team,
                "red_team": self.game_info.red_team,
                "blue_champions": self.game_info.blue_champions,
                "red_champions": self.game_info.red_champions,
                "draft_analysis": self.game_info.draft_analysis,
                "winner": self.game_info.winner,
            },
            "commentary": [c.to_dict() for c in self.commentary],
        }
