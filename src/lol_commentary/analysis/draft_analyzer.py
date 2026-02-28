from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum

from ..riot_api.models import MatchInfo, Participant


class CompArchetype(str, Enum):
    POKE = "poke"
    ENGAGE = "engage"
    SPLIT = "split"
    TEAMFIGHT = "teamfight"
    PICK = "pick"
    PROTECT = "protect"


@dataclass
class TeamAnalysis:
    archetype: CompArchetype
    win_conditions: list[str]
    power_spikes: dict[str, float]  # early/mid/late -> power level (0-1)
    synergies: list[str]
    weaknesses: list[str]


@dataclass
class DraftAnalysis:
    blue_team: TeamAnalysis
    red_team: TeamAnalysis
    matchup_summary: str
    scaling_advantage: str  # "blue" or "red"
    early_advantage: str  # "blue" or "red"


# Champion role classification for archetype detection
ENGAGE_CHAMPIONS = {
    "Malphite", "Amumu", "Leona", "Nautilus", "Rakan", "Ornn", "Sejuani",
    "Zac", "Maokai", "Alistar", "Thresh", "Jarvan IV", "Wukong",
}
POKE_CHAMPIONS = {
    "Jayce", "Ezreal", "Xerath", "Ziggs", "Lux", "Velkoz", "Zoe",
    "Nidalee", "Varus", "Caitlyn", "Karma",
}
SPLIT_CHAMPIONS = {
    "Fiora", "Camille", "Jax", "Tryndamere", "Shen", "Yorick",
    "Nasus", "Udyr", "Gwen",
}
PROTECT_CHAMPIONS = {
    "Lulu", "Janna", "Yuumi", "Soraka", "Nami", "Sona", "Ivern", "Taric",
}

# Scaling tiers
LATE_GAME_CARRIES = {
    "Kayle", "Kassadin", "Vayne", "Jinx", "Kog'Maw", "Aphelios",
    "Azir", "Ryze", "Viktor", "Cassiopeia", "Twitch", "Veigar",
}
EARLY_GAME_CHAMPIONS = {
    "Draven", "Renekton", "Pantheon", "Lee Sin", "Elise", "Nidalee",
    "LeBlanc", "Lucian", "Caitlyn", "Jayce",
}


class DraftAnalyzer:
    def analyze(self, match_info: MatchInfo) -> DraftAnalysis:
        blue = [p for p in match_info.participants if p.team_id == 100]
        red = [p for p in match_info.participants if p.team_id == 200]

        blue_analysis = self._analyze_team(blue)
        red_analysis = self._analyze_team(red)

        # Determine scaling advantage
        blue_late = blue_analysis.power_spikes.get("late", 0)
        red_late = red_analysis.power_spikes.get("late", 0)
        scaling_adv = "blue" if blue_late > red_late else "red"

        blue_early = blue_analysis.power_spikes.get("early", 0)
        red_early = red_analysis.power_spikes.get("early", 0)
        early_adv = "blue" if blue_early > red_early else "red"

        blue_champs = ", ".join(p.champion_name for p in blue)
        red_champs = ", ".join(p.champion_name for p in red)
        summary = (
            f"\u30d6\u30eb\u30fc({blue_champs})\u306f{blue_analysis.archetype.value}\u69cb\u6210\u3002"
            f"\u30ec\u30c3\u30c9({red_champs})\u306f{red_analysis.archetype.value}\u69cb\u6210\u3002"
            f"\u30b9\u30b1\u30fc\u30ea\u30f3\u30b0\u306f{'\u30d6\u30eb\u30fc' if scaling_adv == 'blue' else '\u30ec\u30c3\u30c9'}\u6709\u5229\u3001"
            f"\u5e8f\u76e4\u306f{'\u30d6\u30eb\u30fc' if early_adv == 'blue' else '\u30ec\u30c3\u30c9'}\u6709\u5229\u3002"
        )

        return DraftAnalysis(
            blue_team=blue_analysis,
            red_team=red_analysis,
            matchup_summary=summary,
            scaling_advantage=scaling_adv,
            early_advantage=early_adv,
        )

    def _analyze_team(self, participants: list[Participant]) -> TeamAnalysis:
        champ_names = {p.champion_name for p in participants}

        # Detect archetype
        archetype = self._detect_archetype(champ_names)

        # Power spikes
        power_spikes = self._calculate_power_spikes(champ_names)

        # Win conditions
        win_conditions = self._determine_win_conditions(archetype, champ_names)

        # Synergies
        synergies = self._detect_synergies(champ_names)

        # Weaknesses
        weaknesses = self._detect_weaknesses(archetype, champ_names)

        return TeamAnalysis(
            archetype=archetype,
            win_conditions=win_conditions,
            power_spikes=power_spikes,
            synergies=synergies,
            weaknesses=weaknesses,
        )

    def _detect_archetype(self, champs: set[str]) -> CompArchetype:
        scores = {
            CompArchetype.ENGAGE: len(champs & ENGAGE_CHAMPIONS),
            CompArchetype.POKE: len(champs & POKE_CHAMPIONS),
            CompArchetype.SPLIT: len(champs & SPLIT_CHAMPIONS),
            CompArchetype.PROTECT: len(champs & PROTECT_CHAMPIONS),
        }
        best = max(scores, key=scores.get)
        if scores[best] >= 2:
            return best
        return CompArchetype.TEAMFIGHT  # default

    def _calculate_power_spikes(self, champs: set[str]) -> dict[str, float]:
        late_count = len(champs & LATE_GAME_CARRIES)
        early_count = len(champs & EARLY_GAME_CHAMPIONS)
        total = len(champs) or 1
        return {
            "early": min(1.0, 0.3 + early_count * 0.15),
            "mid": 0.5,
            "late": min(1.0, 0.3 + late_count * 0.15),
        }

    def _determine_win_conditions(self, archetype: CompArchetype, champs: set[str]) -> list[str]:
        conditions = {
            CompArchetype.ENGAGE: ["5v5\u96c6\u56e3\u6226\u3067\u30a8\u30f3\u30b2\u30fc\u30b8\u3092\u6c7a\u3081\u308b", "\u6709\u5229\u306a\u72b6\u614b\u3067\u96c6\u56e3\u6226\u3092\u4ed5\u639b\u3051\u308b"],
            CompArchetype.POKE: ["\u30dd\u30fc\u30af\u3067HP\u3092\u524a\u3063\u3066\u304b\u3089\u30aa\u30d6\u30b8\u30a7\u30af\u30c8\u3092\u53d6\u308b", "\u8996\u754c\u3092\u78ba\u4fdd\u3057\u3066\u30b7\u30fc\u30b8"],
            CompArchetype.SPLIT: ["\u30b5\u30a4\u30c9\u30ec\u30fc\u30f3\u3067\u5727\u529b\u3092\u304b\u3051\u3066\u6570\u7684\u6709\u5229\u3092\u4f5c\u308b", "1-3-1 or 1-4\u3067\u30de\u30c3\u30d7\u3092\u5e83\u3052\u308b"],
            CompArchetype.TEAMFIGHT: ["\u96c6\u56e3\u6226\u3067\u306eAoE\u30c0\u30e1\u30fc\u30b8\u3068CC\u9023\u643a", "\u30aa\u30d6\u30b8\u30a7\u30af\u30c8\u524d\u306e\u96c6\u56e3\u6226\u3067\u52dd\u3064"],
            CompArchetype.PICK: ["\u5c11\u4eba\u6570\u6226\u3067\u30d4\u30c3\u30af\u3092\u53d6\u308b", "\u8996\u754c\u5dee\u3092\u6d3b\u304b\u3057\u3066\u30ad\u30e3\u30c3\u30c1"],
            CompArchetype.PROTECT: ["\u30ad\u30e3\u30ea\u30fc\u3092\u5b88\u308a\u306a\u304c\u3089DPS\u3092\u51fa\u3059", "\u524d\u885b\u304c\u30be\u30fc\u30cb\u30f3\u30b0\u3057\u3066\u3044\u308b\u9593\u306b\u30ad\u30e3\u30ea\u30fc\u304c\u706b\u529b\u3092\u51fa\u3059"],
        }
        return conditions.get(archetype, ["\u6a19\u6e96\u7684\u306a\u52dd\u5229\u6761\u4ef6"])

    def _detect_synergies(self, champs: set[str]) -> list[str]:
        synergies = []
        # AOE wombo combo
        aoe_champs = champs & {"Amumu", "Malphite", "Orianna", "Yasuo", "Miss Fortune", "Jarvan IV"}
        if len(aoe_champs) >= 2:
            synergies.append(f"AoE\u30b3\u30f3\u30dc: {', '.join(aoe_champs)}")
        # Protect the carry
        if champs & PROTECT_CHAMPIONS and champs & LATE_GAME_CARRIES:
            synergies.append("\u30ad\u30e3\u30ea\u30fc\u4fdd\u8b77\u69cb\u6210")
        return synergies

    def _detect_weaknesses(self, archetype: CompArchetype, champs: set[str]) -> list[str]:
        weaknesses = []
        if archetype == CompArchetype.POKE:
            weaknesses.append("\u30cf\u30fc\u30c9\u30a8\u30f3\u30b2\u30fc\u30b8\u306b\u5f31\u3044")
        if archetype == CompArchetype.SPLIT:
            weaknesses.append("5v5\u96c6\u56e3\u6226\u3067\u4e0d\u5229")
        if archetype == CompArchetype.ENGAGE:
            weaknesses.append("\u30c7\u30a3\u30b9\u30a8\u30f3\u30b2\u30fc\u30b8\u306b\u5f31\u3044")
        if len(champs & LATE_GAME_CARRIES) == 0 and len(champs & EARLY_GAME_CHAMPIONS) >= 2:
            weaknesses.append("\u30ec\u30a4\u30c8\u30b2\u30fc\u30e0\u3067\u30b9\u30b1\u30fc\u30ea\u30f3\u30b0\u4e0d\u8db3")
        return weaknesses
