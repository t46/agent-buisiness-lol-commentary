from enum import Enum

from pydantic import BaseModel


class EventType(str, Enum):
    CHAMPION_KILL = "CHAMPION_KILL"
    ELITE_MONSTER_KILL = "ELITE_MONSTER_KILL"
    BUILDING_KILL = "BUILDING_KILL"
    TURRET_PLATE_DESTROYED = "TURRET_PLATE_DESTROYED"
    ITEM_PURCHASED = "ITEM_PURCHASED"
    WARD_PLACED = "WARD_PLACED"
    WARD_KILL = "WARD_KILL"
    LEVEL_UP = "LEVEL_UP"


class MonsterType(str, Enum):
    BARON_NASHOR = "BARON_NASHOR"
    ELDER_DRAGON = "ELDER_DRAGON"
    DRAGON = "DRAGON"
    RIFTHERALD = "RIFTHERALD"
    VOID_GRUB = "VOID_GRUB"


class BuildingType(str, Enum):
    TOWER_BUILDING = "TOWER_BUILDING"
    INHIBITOR_BUILDING = "INHIBITOR_BUILDING"
    NEXUS_BUILDING = "NEXUS_BUILDING"


class Position(BaseModel):
    x: int
    y: int


class TimelineEvent(BaseModel):
    timestamp: int  # milliseconds
    type: str
    killer_id: int | None = None
    victim_id: int | None = None
    assisting_participant_ids: list[int] = []
    position: Position | None = None
    monster_type: str | None = None
    monster_sub_type: str | None = None
    building_type: str | None = None
    lane_type: str | None = None
    tower_type: str | None = None
    item_id: int | None = None
    participant_id: int | None = None
    level: int | None = None
    ward_type: str | None = None


class Participant(BaseModel):
    participant_id: int
    puuid: str
    riot_id_game_name: str | None = None
    riot_id_tagline: str | None = None
    champion_id: int
    champion_name: str
    team_id: int  # 100=blue, 200=red
    role: str | None = None
    lane: str | None = None
    kills: int = 0
    deaths: int = 0
    assists: int = 0
    total_damage_dealt_to_champions: int = 0
    gold_earned: int = 0
    cs: int = 0
    vision_score: int = 0
    items: list[int] = []
    summoner_spells: list[int] = []
    runes: dict | None = None
    win: bool = False


class TeamStats(BaseModel):
    team_id: int
    win: bool
    baron_kills: int = 0
    dragon_kills: int = 0
    tower_kills: int = 0
    inhibitor_kills: int = 0
    rift_herald_kills: int = 0
    bans: list[int] = []


class MatchInfo(BaseModel):
    match_id: str
    game_version: str
    game_duration: int  # seconds
    game_mode: str
    participants: list[Participant]
    teams: list[TeamStats]


class MatchTimeline(BaseModel):
    match_id: str
    frames: list[dict]  # raw frames from API
    events: list[TimelineEvent] = []


class ChampionData(BaseModel):
    id: str
    key: int
    name: str
    title: str
    tags: list[str] = []  # Fighter, Mage, etc.


class ItemData(BaseModel):
    id: int
    name: str
    description: str = ""
    gold_total: int = 0
    gold_base: int = 0
    from_items: list[int] = []
    into_items: list[int] = []
    stats: dict = {}
