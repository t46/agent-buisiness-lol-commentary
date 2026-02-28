from __future__ import annotations
import json
import logging
from .database import Database

logger = logging.getLogger(__name__)


class ChampionKB:
    def __init__(self, db: Database):
        self.db = db

    def upsert_champion(self, champion_id: int, name: str, title: str = "", roles: str = "", resource_type: str = "MANA"):
        self.db.insert("champions", {
            "id": champion_id,
            "name": name,
            "title": title,
            "roles": roles,
            "resource_type": resource_type,
        })

    def get_champion(self, champion_id: int) -> dict | None:
        row = self.db.execute_one("SELECT * FROM champions WHERE id = ?", (champion_id,))
        return dict(row) if row else None

    def get_champion_by_name(self, name: str) -> dict | None:
        row = self.db.execute_one("SELECT * FROM champions WHERE name = ?", (name,))
        return dict(row) if row else None

    def get_all_champions(self) -> list[dict]:
        rows = self.db.execute("SELECT * FROM champions ORDER BY name")
        return [dict(r) for r in rows]

    def upsert_stats(self, champion_id: int, patch: str, role: str, **kwargs):
        data = {"champion_id": champion_id, "patch": patch, "role": role}
        data.update(kwargs)
        self.db.insert("champion_stats", data)

    def get_stats(self, champion_id: int, patch: str | None = None, role: str | None = None) -> list[dict]:
        query = "SELECT * FROM champion_stats WHERE champion_id = ?"
        params = [champion_id]
        if patch:
            query += " AND patch = ?"
            params.append(patch)
        if role:
            query += " AND role = ?"
            params.append(role)
        rows = self.db.execute(query, tuple(params))
        return [dict(r) for r in rows]

    def upsert_matchup(self, champion_id: int, opponent_id: int, role: str, win_rate: float = 0.5, gold_diff_15: float = 0.0, sample_size: int = 0):
        self.db.insert("champion_matchups", {
            "champion_id": champion_id,
            "opponent_id": opponent_id,
            "role": role,
            "win_rate": win_rate,
            "gold_diff_15": gold_diff_15,
            "sample_size": sample_size,
        })

    def get_matchup(self, champion_id: int, opponent_id: int, role: str | None = None) -> dict | None:
        query = "SELECT * FROM champion_matchups WHERE champion_id = ? AND opponent_id = ?"
        params = [champion_id, opponent_id]
        if role:
            query += " AND role = ?"
            params.append(role)
        row = self.db.execute_one(query, tuple(params))
        return dict(row) if row else None

    def bulk_update_from_data_dragon(self, champions: dict):
        """Update champion data from Data Dragon response."""
        for key, champ_data in champions.items():
            self.upsert_champion(
                champion_id=int(champ_data.get("key", 0)),
                name=champ_data.get("name", key),
                title=champ_data.get("title", ""),
                roles=",".join(champ_data.get("tags", [])),
            )
        logger.info(f"Updated {len(champions)} champions from Data Dragon")
