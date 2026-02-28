from __future__ import annotations
from dataclasses import dataclass, field

from ..riot_api.models import MatchInfo, MatchTimeline, TimelineEvent


@dataclass
class ObjectiveTimeline:
    dragons: list[dict] = field(default_factory=list)  # team, type, time
    barons: list[dict] = field(default_factory=list)
    heralds: list[dict] = field(default_factory=list)
    towers: list[dict] = field(default_factory=list)


@dataclass
class GoldDistribution:
    total: int
    by_role: dict[str, int] = field(default_factory=dict)
    carry_percentage: float = 0.0  # % of gold on top 2 earners
    distribution_type: str = ""  # "carry_focused" or "spread"


@dataclass
class TeamMacroAnalysis:
    team_id: int
    team_name: str  # "blue" or "red"
    objective_timeline: ObjectiveTimeline
    gold_distribution: GoldDistribution
    vision_score_total: int = 0
    tower_plates_taken: int = 0
    first_tower: bool = False
    first_blood: bool = False
    macro_rating: str = ""  # "strong", "average", "weak"
    key_observations: list[str] = field(default_factory=list)


class TeamAnalyzer:
    """Analyzes team-level macro strategy from match data."""

    def analyze(self, match_info: MatchInfo, events: list[TimelineEvent]) -> dict[str, TeamMacroAnalysis]:
        blue = self._analyze_team(100, "blue", match_info, events)
        red = self._analyze_team(200, "red", match_info, events)

        # Compare and add observations
        self._add_comparative_observations(blue, red, match_info)

        return {"blue": blue, "red": red}

    def _analyze_team(self, team_id: int, team_name: str,
                      match_info: MatchInfo, events: list[TimelineEvent]) -> TeamMacroAnalysis:
        participants = [p for p in match_info.participants if p.team_id == team_id]

        # Objective timeline
        obj_timeline = self._build_objective_timeline(team_id, events, match_info)

        # Gold distribution
        gold_dist = self._analyze_gold_distribution(participants)

        # Vision
        vision_total = sum(p.vision_score for p in participants)

        # Tower plates
        plates = sum(1 for e in events if e.type == "TURRET_PLATE_DESTROYED"
                     and self._event_by_team(e, team_id, match_info))

        # First tower / first blood
        first_tower = self._check_first(events, "BUILDING_KILL", team_id, match_info)
        first_blood = self._check_first(events, "CHAMPION_KILL", team_id, match_info)

        analysis = TeamMacroAnalysis(
            team_id=team_id,
            team_name=team_name,
            objective_timeline=obj_timeline,
            gold_distribution=gold_dist,
            vision_score_total=vision_total,
            tower_plates_taken=plates,
            first_tower=first_tower,
            first_blood=first_blood,
        )

        self._rate_macro(analysis)
        return analysis

    def _build_objective_timeline(self, team_id: int, events: list[TimelineEvent],
                                   match_info: MatchInfo) -> ObjectiveTimeline:
        timeline = ObjectiveTimeline()
        for event in events:
            if event.type != "ELITE_MONSTER_KILL":
                continue
            if not self._event_by_team(event, team_id, match_info):
                continue
            entry = {
                "time": event.timestamp,
                "time_str": f"{event.timestamp // 60000}:{(event.timestamp // 1000) % 60:02d}",
                "type": event.monster_sub_type or event.monster_type,
            }
            if event.monster_type == "BARON_NASHOR":
                timeline.barons.append(entry)
            elif event.monster_type in ("DRAGON", "ELDER_DRAGON"):
                timeline.dragons.append(entry)
            elif event.monster_type == "RIFTHERALD":
                timeline.heralds.append(entry)

        for event in events:
            if event.type == "BUILDING_KILL" and self._event_by_team(event, team_id, match_info):
                if event.building_type == "TOWER_BUILDING":
                    timeline.towers.append({
                        "time": event.timestamp,
                        "lane": event.lane_type,
                    })
        return timeline

    def _analyze_gold_distribution(self, participants: list) -> GoldDistribution:
        total = sum(p.gold_earned for p in participants)
        if total == 0:
            return GoldDistribution(total=0)

        by_role = {}
        for p in participants:
            role = p.lane or p.role or "UNKNOWN"
            by_role[role] = p.gold_earned

        sorted_gold = sorted((p.gold_earned for p in participants), reverse=True)
        top2 = sum(sorted_gold[:2])
        carry_pct = top2 / total if total > 0 else 0

        dist_type = "carry_focused" if carry_pct > 0.5 else "spread"

        return GoldDistribution(
            total=total,
            by_role=by_role,
            carry_percentage=carry_pct,
            distribution_type=dist_type,
        )

    def _event_by_team(self, event: TimelineEvent, team_id: int, match_info: MatchInfo) -> bool:
        if event.killer_id is None:
            return False
        for p in match_info.participants:
            if p.participant_id == event.killer_id:
                return p.team_id == team_id
        return False

    def _check_first(self, events: list[TimelineEvent], event_type: str,
                     team_id: int, match_info: MatchInfo) -> bool:
        for event in events:
            if event.type == event_type:
                return self._event_by_team(event, team_id, match_info)
        return False

    def _rate_macro(self, analysis: TeamMacroAnalysis):
        score = 0
        observations = []

        if analysis.first_tower:
            score += 1
            observations.append("\u30d5\u30a1\u30fc\u30b9\u30c8\u30bf\u30ef\u30fc\u7372\u5f97")
        if analysis.first_blood:
            score += 0.5
            observations.append("\u30d5\u30a1\u30fc\u30b9\u30c8\u30d6\u30e9\u30c3\u30c9")
        if analysis.tower_plates_taken >= 3:
            score += 1
            observations.append(f"\u30bf\u30ef\u30fc\u30d7\u30ec\u30fc\u30c8{analysis.tower_plates_taken}\u679a\u7372\u5f97")
        if analysis.vision_score_total >= 100:
            score += 1
            observations.append("\u30d3\u30b8\u30e7\u30f3\u30b3\u30f3\u30c8\u30ed\u30fc\u30eb\u826f\u597d")
        if len(analysis.objective_timeline.dragons) >= 2:
            score += 1
            observations.append(f"\u30c9\u30e9\u30b4\u30f3{len(analysis.objective_timeline.dragons)}\u4f53\u78ba\u4fdd")

        if score >= 3:
            analysis.macro_rating = "strong"
        elif score >= 1.5:
            analysis.macro_rating = "average"
        else:
            analysis.macro_rating = "weak"

        analysis.key_observations = observations

    def _add_comparative_observations(self, blue: TeamMacroAnalysis, red: TeamMacroAnalysis,
                                       match_info: MatchInfo):
        gold_diff = blue.gold_distribution.total - red.gold_distribution.total
        if abs(gold_diff) > 3000:
            leader = blue if gold_diff > 0 else red
            leader.key_observations.append(f"\u30b4\u30fc\u30eb\u30c9\u5dee{abs(gold_diff):,}G\u6709\u5229")

        if blue.vision_score_total > red.vision_score_total * 1.3:
            blue.key_observations.append("\u30d3\u30b8\u30e7\u30f3\u3067\u5927\u304d\u304f\u512a\u4f4d")
        elif red.vision_score_total > blue.vision_score_total * 1.3:
            red.key_observations.append("\u30d3\u30b8\u30e7\u30f3\u3067\u5927\u304d\u304f\u512a\u4f4d")
