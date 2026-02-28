from __future__ import annotations
import json
import logging
from .database import Database

logger = logging.getLogger(__name__)


class MetaKB:
    def __init__(self, db: Database):
        self.db = db

    def upsert_snapshot(self, patch: str, tier: str = "all", role: str = "all",
                        top_champions: list[str] | None = None,
                        banned_champions: list[str] | None = None,
                        meta_notes: str = ""):
        self.db.insert("meta_snapshots", {
            "patch": patch,
            "tier": tier,
            "role": role,
            "top_champions": json.dumps(top_champions or []),
            "banned_champions": json.dumps(banned_champions or []),
            "meta_notes": meta_notes,
        })

    def get_snapshot(self, patch: str, tier: str = "all", role: str = "all") -> dict | None:
        row = self.db.execute_one(
            "SELECT * FROM meta_snapshots WHERE patch = ? AND tier = ? AND role = ?",
            (patch, tier, role),
        )
        if row:
            result = dict(row)
            result["top_champions"] = json.loads(result["top_champions"]) if result["top_champions"] else []
            result["banned_champions"] = json.loads(result["banned_champions"]) if result["banned_champions"] else []
            return result
        return None

    def get_latest_snapshot(self, tier: str = "all", role: str = "all") -> dict | None:
        row = self.db.execute_one(
            "SELECT * FROM meta_snapshots WHERE tier = ? AND role = ? ORDER BY created_at DESC LIMIT 1",
            (tier, role),
        )
        if row:
            result = dict(row)
            result["top_champions"] = json.loads(result["top_champions"]) if result["top_champions"] else []
            result["banned_champions"] = json.loads(result["banned_champions"]) if result["banned_champions"] else []
            return result
        return None

    def record_analyzed_game(self, match_id: str, patch: str, duration: int, winner: str,
                              blue_comp: list[str], red_comp: list[str], analysis: dict):
        self.db.insert("analyzed_games", {
            "match_id": match_id,
            "patch": patch,
            "duration": duration,
            "winner": winner,
            "blue_team_comp": json.dumps(blue_comp),
            "red_team_comp": json.dumps(red_comp),
            "analysis_json": json.dumps(analysis),
        })

    def record_play_pattern(self, pattern_type: str, description: str, rating: str, context: dict):
        existing = self.db.execute_one(
            "SELECT * FROM play_patterns WHERE pattern_type = ? AND description = ?",
            (pattern_type, description),
        )
        if existing:
            self.db.update("play_patterns",
                {"frequency": existing["frequency"] + 1, "rating": rating, "context_json": json.dumps(context)},
                "id = ?", (existing["id"],))
        else:
            self.db.insert("play_patterns", {
                "pattern_type": pattern_type,
                "description": description,
                "rating": rating,
                "context_json": json.dumps(context),
            })
