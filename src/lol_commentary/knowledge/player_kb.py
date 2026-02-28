from __future__ import annotations
import logging
from .database import Database

logger = logging.getLogger(__name__)


class PlayerKB:
    def __init__(self, db: Database):
        self.db = db

    def upsert_player(self, puuid: str, riot_id: str, tag_line: str = "", region: str = "jp1", **kwargs):
        data = {
            "puuid": puuid,
            "riot_id": riot_id,
            "tag_line": tag_line,
            "region": region,
        }
        data.update(kwargs)
        self.db.insert("players", data)

    def get_player(self, puuid: str) -> dict | None:
        row = self.db.execute_one("SELECT * FROM players WHERE puuid = ?", (puuid,))
        return dict(row) if row else None

    def find_player_by_name(self, riot_id: str) -> dict | None:
        row = self.db.execute_one("SELECT * FROM players WHERE riot_id = ?", (riot_id,))
        return dict(row) if row else None

    def update_champion_pool(self, puuid: str, champion_id: int, games_played: int, win_rate: float, avg_kda: float):
        self.db.insert("player_champion_pool", {
            "puuid": puuid,
            "champion_id": champion_id,
            "games_played": games_played,
            "win_rate": win_rate,
            "avg_kda": avg_kda,
        })

    def get_champion_pool(self, puuid: str) -> list[dict]:
        rows = self.db.execute(
            """SELECT pc.*, c.name as champion_name
               FROM player_champion_pool pc
               JOIN champions c ON pc.champion_id = c.id
               WHERE pc.puuid = ?
               ORDER BY pc.games_played DESC""",
            (puuid,),
        )
        return [dict(r) for r in rows]

    def update_from_match(self, puuid: str, champion_id: int, won: bool, kills: int, deaths: int, assists: int):
        """Update player stats from a match result."""
        existing = self.db.execute_one(
            "SELECT * FROM player_champion_pool WHERE puuid = ? AND champion_id = ?",
            (puuid, champion_id),
        )
        if existing:
            games = existing["games_played"] + 1
            new_wr = ((existing["win_rate"] * existing["games_played"]) + (1.0 if won else 0.0)) / games
            kda = (kills + assists) / max(deaths, 1)
            new_kda = ((existing["avg_kda"] * existing["games_played"]) + kda) / games
            self.update_champion_pool(puuid, champion_id, games, new_wr, new_kda)
        else:
            kda = (kills + assists) / max(deaths, 1)
            self.update_champion_pool(puuid, champion_id, 1, 1.0 if won else 0.0, kda)
