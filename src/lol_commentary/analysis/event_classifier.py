from __future__ import annotations
from dataclasses import dataclass, field

from ..riot_api.models import TimelineEvent


@dataclass
class ImportanceScore:
    total: float
    breakdown: dict[str, float] = field(default_factory=dict)
    reason: str = ""


class EventClassifier:
    # Objective positions (approximate, Summoner's Rift)
    BARON_POS = (5064, 10548)
    DRAGON_POS = (9866, 4414)
    OBJECTIVE_RADIUS = 3000

    def classify(self, event: TimelineEvent, context: dict | None = None) -> ImportanceScore:
        """Score the importance of an event (0.0 to 1.0)."""
        context = context or {}

        if event.type == "CHAMPION_KILL":
            return self._score_kill(event, context)
        elif event.type == "ELITE_MONSTER_KILL":
            return self._score_monster(event, context)
        elif event.type == "BUILDING_KILL":
            return self._score_building(event, context)
        elif event.type == "TURRET_PLATE_DESTROYED":
            return ImportanceScore(total=0.2, breakdown={"base": 0.2}, reason="Tower plate destroyed")
        elif event.type == "LEVEL_UP":
            return self._score_level_up(event, context)
        else:
            return ImportanceScore(total=0.1, breakdown={"base": 0.1})

    def _score_kill(self, event: TimelineEvent, context: dict) -> ImportanceScore:
        score = 0.4
        breakdown = {"base": 0.4}
        reasons = []

        # First blood
        if context.get("is_first_blood"):
            score += 0.1
            breakdown["first_blood"] = 0.1
            reasons.append("\u30d5\u30a1\u30fc\u30b9\u30c8\u30d6\u30e9\u30c3\u30c9")

        # Kill streak
        streak = context.get("kill_streak", 0)
        if streak >= 3:
            bonus = min(0.3, streak * 0.1)
            score += bonus
            breakdown["kill_streak"] = bonus
            reasons.append(f"{streak}\u30ad\u30eb\u30b9\u30c8\u30ea\u30fc\u30af")

        # Shutdown
        if context.get("shutdown_bounty", 0) > 0:
            score += 0.15
            breakdown["shutdown"] = 0.15
            reasons.append("\u30b7\u30e3\u30c3\u30c8\u30c0\u30a6\u30f3")

        # Near objective
        if event.position and self._near_objective(event.position.x, event.position.y):
            score += 0.1
            breakdown["near_objective"] = 0.1
            reasons.append("\u30aa\u30d6\u30b8\u30a7\u30af\u30c8\u4ed8\u8fd1")

        # Multi-kill / teamfight context
        assists = len(event.assisting_participant_ids)
        if assists >= 3:
            score += 0.2
            breakdown["teamfight"] = 0.2
            reasons.append("\u96c6\u56e3\u6226")

        return ImportanceScore(
            total=min(1.0, score),
            breakdown=breakdown,
            reason="\u3001".join(reasons) if reasons else "\u30ad\u30eb",
        )

    def _score_monster(self, event: TimelineEvent, context: dict) -> ImportanceScore:
        monster = event.monster_type or ""
        sub_type = event.monster_sub_type or ""

        scores = {
            "BARON_NASHOR": (0.9, "\u30d0\u30ed\u30f3\u30ca\u30c3\u30b7\u30e5\u30fc"),
            "ELDER_DRAGON": (0.95, "\u30a8\u30eb\u30c0\u30fc\u30c9\u30e9\u30b4\u30f3"),
            "RIFTHERALD": (0.4, "\u30ea\u30d5\u30c8\u30d8\u30e9\u30eb\u30c9"),
            "VOID_GRUB": (0.3, "\u30f4\u30a9\u30a4\u30c9\u30b0\u30e9\u30d6"),
        }

        if monster in scores:
            s, name = scores[monster]
            return ImportanceScore(total=s, breakdown={"base": s}, reason=f"{name}\u8a0e\u4f10")

        if monster == "DRAGON":
            # Check if it's a soul dragon
            dragon_count = context.get("dragon_count", 0)
            if dragon_count >= 3:
                return ImportanceScore(total=0.8, breakdown={"base": 0.8}, reason="\u30c9\u30e9\u30b4\u30f3\u30bd\u30a6\u30eb\u7372\u5f97")
            return ImportanceScore(total=0.5, breakdown={"base": 0.5}, reason=f"\u30c9\u30e9\u30b4\u30f3\u8a0e\u4f10({sub_type})")

        return ImportanceScore(total=0.4, breakdown={"base": 0.4}, reason="\u30e2\u30f3\u30b9\u30bf\u30fc\u8a0e\u4f10")

    def _score_building(self, event: TimelineEvent, context: dict) -> ImportanceScore:
        building = event.building_type or ""
        scores = {
            "NEXUS_BUILDING": (1.0, "\u30cd\u30af\u30b5\u30b9\u7834\u58ca"),
            "INHIBITOR_BUILDING": (0.7, "\u30a4\u30f3\u30d2\u30d3\u30bf\u30fc\u7834\u58ca"),
            "TOWER_BUILDING": (0.5, "\u30bf\u30ef\u30fc\u7834\u58ca"),
        }
        s, name = scores.get(building, (0.3, "\u5efa\u7269\u7834\u58ca"))
        return ImportanceScore(total=s, breakdown={"base": s}, reason=name)

    def _score_level_up(self, event: TimelineEvent, context: dict) -> ImportanceScore:
        level = event.level or 0
        if level == 6:
            return ImportanceScore(total=0.3, breakdown={"base": 0.3}, reason="Lv6\u5230\u9054(\u30a2\u30eb\u30c6\u30a3\u30e1\u30c3\u30c8\u89e3\u7981)")
        if level in (11, 16):
            return ImportanceScore(total=0.2, breakdown={"base": 0.2}, reason=f"Lv{level}(\u30a2\u30eb\u30c6\u30a3\u30e1\u30c3\u30c8\u5f37\u5316)")
        return ImportanceScore(total=0.05, breakdown={"base": 0.05}, reason=f"Lv{level}")

    def _near_objective(self, x: int, y: int) -> bool:
        for ox, oy in [self.BARON_POS, self.DRAGON_POS]:
            dist = ((x - ox) ** 2 + (y - oy) ** 2) ** 0.5
            if dist < self.OBJECTIVE_RADIUS:
                return True
        return False
