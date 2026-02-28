from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum

from ..riot_api.models import TimelineEvent, MatchInfo


class PlayRating(str, Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    NEUTRAL = "neutral"
    QUESTIONABLE = "questionable"
    POOR = "poor"


@dataclass
class PlayEvaluation:
    rating: PlayRating
    reason: str
    impact: str  # what effect this had on the game
    lesson: str  # what can be learned
    axes: dict[str, float] = field(default_factory=dict)  # evaluation axis scores


class PlayEvaluator:
    """Evaluates individual plays for quality and significance."""

    def evaluate_kill(self, event: TimelineEvent, match_info: MatchInfo,
                      context: dict | None = None) -> PlayEvaluation:
        """Evaluate a kill event."""
        context = context or {}
        axes = {}

        # Trade efficiency: was this a clean kill or did they trade?
        assists = len(event.assisting_participant_ids)
        is_solo = assists == 0
        axes["trade_efficiency"] = 0.8 if is_solo else 0.5

        # Timing
        game_minute = event.timestamp / 60000
        if game_minute < 5:
            axes["timing"] = 0.7  # early kills are impactful
        elif game_minute < 15:
            axes["timing"] = 0.5
        else:
            axes["timing"] = 0.3

        # Objective conversion potential
        axes["objective_conversion"] = 0.5  # would need post-event analysis

        avg_score = sum(axes.values()) / len(axes) if axes else 0.5
        rating = self._score_to_rating(avg_score)

        # Determine killer/victim info
        killer = self._get_participant(match_info, event.killer_id)
        victim = self._get_participant(match_info, event.victim_id)

        killer_name = killer.riot_id_game_name if killer else "Unknown"
        victim_name = victim.riot_id_game_name if victim else "Unknown"
        killer_champ = killer.champion_name if killer else "Unknown"
        victim_champ = victim.champion_name if victim else "Unknown"

        if is_solo:
            reason = f"{killer_name}({killer_champ})\u304c\u30bd\u30ed\u30ad\u30eb\u30021v1\u3067\u52dd\u5229"
        else:
            reason = f"{killer_name}({killer_champ})\u304c{victim_name}({victim_champ})\u3092\u30ad\u30eb({assists}\u4eba\u30a2\u30b7\u30b9\u30c8)"

        return PlayEvaluation(
            rating=rating,
            reason=reason,
            impact=f"{'\u5e8f\u76e4' if game_minute < 10 else '\u4e2d\u76e4\u4ee5\u964d'}\u306e\u30ad\u30eb\u3067\u30ec\u30fc\u30f3\u4e3b\u5c0e\u6a29\u306b\u5f71\u97ff",
            lesson=self._generate_lesson(event, context),
            axes=axes,
        )

    def evaluate_objective(self, event: TimelineEvent, match_info: MatchInfo,
                           context: dict | None = None) -> PlayEvaluation:
        """Evaluate an objective take."""
        context = context or {}
        monster = event.monster_type or ""
        axes = {}

        # Was it contested?
        is_contested = context.get("contested", False)
        axes["execution"] = 0.7 if not is_contested else 0.5

        # Timing: was it taken at the right time?
        axes["timing"] = 0.6

        # Team coordination
        assists = len(event.assisting_participant_ids)
        axes["coordination"] = min(1.0, assists / 4)

        avg_score = sum(axes.values()) / len(axes) if axes else 0.5
        rating = self._score_to_rating(avg_score)

        team = self._get_participant(match_info, event.killer_id)
        team_name = "\u30d6\u30eb\u30fc" if (team and team.team_id == 100) else "\u30ec\u30c3\u30c9"

        objective_names = {
            "BARON_NASHOR": "\u30d0\u30ed\u30f3",
            "DRAGON": "\u30c9\u30e9\u30b4\u30f3",
            "ELDER_DRAGON": "\u30a8\u30eb\u30c0\u30fc\u30c9\u30e9\u30b4\u30f3",
            "RIFTHERALD": "\u30d8\u30e9\u30eb\u30c9",
            "VOID_GRUB": "\u30f4\u30a9\u30a4\u30c9\u30b0\u30e9\u30d6",
        }
        obj_name = objective_names.get(monster, monster)

        return PlayEvaluation(
            rating=rating,
            reason=f"{team_name}\u30c1\u30fc\u30e0\u304c{obj_name}\u3092\u7372\u5f97",
            impact=f"{obj_name}\u30d0\u30d5\u306b\u3088\u308b\u30de\u30c3\u30d7\u5727\u529b\u306e\u5909\u5316",
            lesson="\u30aa\u30d6\u30b8\u30a7\u30af\u30c8\u30b3\u30f3\u30c8\u30ed\u30fc\u30eb\u306e\u91cd\u8981\u6027",
            axes=axes,
        )

    def _score_to_rating(self, score: float) -> PlayRating:
        if score >= 0.8:
            return PlayRating.EXCELLENT
        elif score >= 0.6:
            return PlayRating.GOOD
        elif score >= 0.4:
            return PlayRating.NEUTRAL
        elif score >= 0.2:
            return PlayRating.QUESTIONABLE
        return PlayRating.POOR

    def _get_participant(self, match_info: MatchInfo, participant_id: int | None):
        if participant_id is None:
            return None
        for p in match_info.participants:
            if p.participant_id == participant_id:
                return p
        return None

    def _generate_lesson(self, event: TimelineEvent, context: dict) -> str:
        game_min = event.timestamp / 60000
        if game_min < 3:
            return "\u5e8f\u76e4\u306e\u30ec\u30d9\u30eb\u5dee\u3092\u6d3b\u304b\u3057\u305f\u30c8\u30ec\u30fc\u30c9\u304c\u91cd\u8981"
        elif game_min < 10:
            return "\u30ec\u30fc\u30cb\u30f3\u30b0\u30d5\u30a7\u30fc\u30ba\u3067\u306e\u4e3b\u5c0e\u6a29\u78ba\u4fdd\u304c\u30df\u30c3\u30c9\u30b2\u30fc\u30e0\u306b\u5f71\u97ff"
        elif game_min < 20:
            return "\u4e2d\u76e4\u306e\u30ed\u30fc\u30c6\u30fc\u30b7\u30e7\u30f3\u3068\u30aa\u30d6\u30b8\u30a7\u30af\u30c8\u5224\u65ad\u304c\u8a66\u5408\u3092\u5de6\u53f3\u3059\u308b"
        return "\u7d42\u76e4\u3067\u306f\u30dd\u30b8\u30b7\u30e7\u30cb\u30f3\u30b0\u3068\u30a8\u30f3\u30b2\u30fc\u30b8\u30bf\u30a4\u30df\u30f3\u30b0\u304c\u6c7a\u5b9a\u7684"
