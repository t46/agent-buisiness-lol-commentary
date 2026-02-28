import hashlib
import json
import time
from pathlib import Path

from riotwatcher import LolWatcher

from .models import MatchInfo, Participant, TeamStats


class RiotAPIClient:
    def __init__(
        self,
        api_key: str,
        region: str = "jp1",
        cache_dir: Path = Path("data/cache"),
        cache_ttl: int = 86400,
    ):
        self.watcher = LolWatcher(api_key)
        self.region = region
        self.cache_dir = cache_dir
        self.cache_ttl = cache_ttl
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_key(self, method: str, *args) -> str:
        raw = f"{method}:{':'.join(str(a) for a in args)}"
        return hashlib.md5(raw.encode()).hexdigest()

    def _get_cached(self, key: str):
        cache_file = self.cache_dir / f"{key}.json"
        if cache_file.exists():
            data = json.loads(cache_file.read_text())
            if time.time() - data["cached_at"] < self.cache_ttl:
                return data["response"]
        return None

    def _set_cache(self, key: str, response):
        cache_file = self.cache_dir / f"{key}.json"
        cache_file.write_text(json.dumps({"cached_at": time.time(), "response": response}))

    def get_account_by_riot_id(self, game_name: str, tag_line: str) -> dict:
        """Use account-v1 to get PUUID from Riot ID."""
        key = self._cache_key("account", game_name, tag_line)
        cached = self._get_cached(key)
        if cached:
            return cached
        result = self.watcher.account.by_riot_id("asia", game_name, tag_line)
        self._set_cache(key, result)
        return result

    def get_match(self, match_id: str) -> MatchInfo:
        """Fetch match data and parse into MatchInfo model."""
        key = self._cache_key("match", match_id)
        cached = self._get_cached(key)
        if not cached:
            cached = self.watcher.match.by_id("asia", match_id)
            self._set_cache(key, cached)

        info = cached["info"]
        participants = []
        for p in info["participants"]:
            participants.append(
                Participant(
                    participant_id=p["participantId"],
                    puuid=p["puuid"],
                    riot_id_game_name=p.get("riotIdGameName"),
                    riot_id_tagline=p.get("riotIdTagline"),
                    champion_id=p["championId"],
                    champion_name=p["championName"],
                    team_id=p["teamId"],
                    role=p.get("role"),
                    lane=p.get("lane"),
                    kills=p.get("kills", 0),
                    deaths=p.get("deaths", 0),
                    assists=p.get("assists", 0),
                    total_damage_dealt_to_champions=p.get("totalDamageDealtToChampions", 0),
                    gold_earned=p.get("goldEarned", 0),
                    cs=p.get("totalMinionsKilled", 0) + p.get("neutralMinionsKilled", 0),
                    vision_score=p.get("visionScore", 0),
                    items=[p.get(f"item{i}", 0) for i in range(7)],
                    summoner_spells=[p.get("summoner1Id", 0), p.get("summoner2Id", 0)],
                    win=p.get("win", False),
                )
            )

        teams = []
        for t in info["teams"]:
            teams.append(
                TeamStats(
                    team_id=t["teamId"],
                    win=t["win"],
                    baron_kills=t["objectives"]["baron"]["kills"],
                    dragon_kills=t["objectives"]["dragon"]["kills"],
                    tower_kills=t["objectives"]["tower"]["kills"],
                    inhibitor_kills=t["objectives"]["inhibitor"]["kills"],
                    rift_herald_kills=t["objectives"]["riftHerald"]["kills"],
                    bans=[b["championId"] for b in t.get("bans", [])],
                )
            )

        return MatchInfo(
            match_id=match_id,
            game_version=info["gameVersion"],
            game_duration=info["gameDuration"],
            game_mode=info["gameMode"],
            participants=participants,
            teams=teams,
        )

    def get_match_timeline(self, match_id: str) -> dict:
        """Fetch raw match timeline data."""
        key = self._cache_key("timeline", match_id)
        cached = self._get_cached(key)
        if cached:
            return cached
        result = self.watcher.match.timeline_by_match("asia", match_id)
        self._set_cache(key, result)
        return result

    def get_match_list(
        self,
        puuid: str,
        count: int = 20,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> list[str]:
        """Fetch list of match IDs for a player."""
        key = self._cache_key("matchlist", puuid, count, start_time, end_time)
        cached = self._get_cached(key)
        if cached:
            return cached
        kwargs: dict = {"count": count}
        if start_time:
            kwargs["start_time"] = start_time
        if end_time:
            kwargs["end_time"] = end_time
        result = self.watcher.match.matchlist_by_puuid("asia", puuid, **kwargs)
        self._set_cache(key, result)
        return result
