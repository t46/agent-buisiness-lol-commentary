import json
import pytest
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_match_info():
    """Sample match info response from Riot API."""
    return {
        "metadata": {"matchId": "JP1_123456789"},
        "info": {
            "gameVersion": "15.4.123.456",
            "gameDuration": 1935,
            "gameMode": "CLASSIC",
            "participants": [
                {
                    "participantId": i + 1,
                    "puuid": f"puuid-{i}",
                    "riotIdGameName": f"Player{i + 1}",
                    "riotIdTagline": "JP1",
                    "championId": 100 + i,
                    "championName": ["Darius", "LeeSin", "Ahri", "Jinx", "Thresh",
                                      "Garen", "Vi", "Lux", "Caitlyn", "Leona"][i],
                    "teamId": 100 if i < 5 else 200,
                    "role": "SOLO",
                    "lane": ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY",
                             "TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"][i],
                    "kills": [5, 8, 3, 7, 1, 2, 4, 6, 3, 0][i],
                    "deaths": [2, 3, 4, 2, 5, 6, 3, 2, 5, 4][i],
                    "assists": [3, 5, 7, 2, 12, 1, 6, 4, 3, 8][i],
                    "totalDamageDealtToChampions": 25000 + i * 1000,
                    "goldEarned": 12000 + i * 500,
                    "totalMinionsKilled": 180 + i * 10,
                    "neutralMinionsKilled": 20 + i * 5,
                    "visionScore": 20 + i * 3,
                    "item0": 3071, "item1": 3006, "item2": 3053,
                    "item3": 3065, "item4": 3143, "item5": 0, "item6": 3340,
                    "summoner1Id": 4, "summoner2Id": 14,
                    "win": i < 5,
                }
                for i in range(10)
            ],
            "teams": [
                {
                    "teamId": 100,
                    "win": True,
                    "objectives": {
                        "baron": {"kills": 1},
                        "dragon": {"kills": 3},
                        "tower": {"kills": 8},
                        "inhibitor": {"kills": 2},
                        "riftHerald": {"kills": 1},
                    },
                    "bans": [{"championId": 200 + i} for i in range(5)],
                },
                {
                    "teamId": 200,
                    "win": False,
                    "objectives": {
                        "baron": {"kills": 0},
                        "dragon": {"kills": 1},
                        "tower": {"kills": 3},
                        "inhibitor": {"kills": 0},
                        "riftHerald": {"kills": 0},
                    },
                    "bans": [{"championId": 210 + i} for i in range(5)],
                },
            ],
        },
    }


@pytest.fixture
def sample_timeline():
    """Sample match timeline response from Riot API."""
    return {
        "info": {
            "frames": [
                {
                    "timestamp": 0,
                    "events": [
                        {"type": "ITEM_PURCHASED", "timestamp": 5000, "participantId": 1, "itemId": 1055},
                    ],
                    "participantFrames": {},
                },
                {
                    "timestamp": 60000,
                    "events": [
                        {"type": "WARD_PLACED", "timestamp": 75000, "wardType": "YELLOW_TRINKET", "creatorId": 5},
                        {"type": "LEVEL_UP", "timestamp": 90000, "participantId": 1, "level": 2},
                    ],
                    "participantFrames": {},
                },
                {
                    "timestamp": 300000,
                    "events": [
                        {
                            "type": "CHAMPION_KILL",
                            "timestamp": 320000,
                            "killerId": 2,
                            "victimId": 8,
                            "assistingParticipantIds": [3],
                            "position": {"x": 7500, "y": 7500},
                        },
                    ],
                    "participantFrames": {},
                },
                {
                    "timestamp": 900000,
                    "events": [
                        {
                            "type": "ELITE_MONSTER_KILL",
                            "timestamp": 920000,
                            "killerId": 2,
                            "monsterType": "DRAGON",
                            "monsterSubType": "FIRE_DRAGON",
                            "position": {"x": 9866, "y": 4414},
                        },
                    ],
                    "participantFrames": {},
                },
                {
                    "timestamp": 1200000,
                    "events": [
                        {
                            "type": "BUILDING_KILL",
                            "timestamp": 1250000,
                            "killerId": 4,
                            "buildingType": "TOWER_BUILDING",
                            "laneType": "BOT_LANE",
                            "towerType": "OUTER_TURRET",
                            "position": {"x": 13866, "y": 4505},
                        },
                    ],
                    "participantFrames": {},
                },
            ],
        },
    }


@pytest.fixture
def sample_timeline_events():
    """Pre-parsed timeline events for testing."""
    from lol_commentary.riot_api.models import TimelineEvent, Position
    return [
        TimelineEvent(
            timestamp=320000, type="CHAMPION_KILL",
            killer_id=2, victim_id=8,
            assisting_participant_ids=[3],
            position=Position(x=7500, y=7500),
        ),
        TimelineEvent(
            timestamp=920000, type="ELITE_MONSTER_KILL",
            killer_id=2, monster_type="DRAGON",
            monster_sub_type="FIRE_DRAGON",
            position=Position(x=9866, y=4414),
        ),
        TimelineEvent(
            timestamp=1250000, type="BUILDING_KILL",
            killer_id=4, building_type="TOWER_BUILDING",
            lane_type="BOT_LANE",
            position=Position(x=13866, y=4505),
        ),
    ]
