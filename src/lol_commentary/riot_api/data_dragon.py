import json
from pathlib import Path

import httpx

from .models import ChampionData, ItemData

DDRAGON_BASE = "https://ddragon.leagueoflegends.com"


class DataDragonClient:
    def __init__(self, cache_dir: Path = Path("data/cache/ddragon")):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._version: str | None = None

    def get_latest_version(self) -> str:
        """Fetch the latest Data Dragon version."""
        if self._version:
            return self._version

        version_file = self.cache_dir / "version.json"
        # Try cached version first
        if version_file.exists():
            cached = json.loads(version_file.read_text())
            self._version = cached["version"]
            return self._version

        resp = httpx.get(f"{DDRAGON_BASE}/api/versions.json")
        resp.raise_for_status()
        versions = resp.json()
        self._version = versions[0]

        version_file.write_text(json.dumps({"version": self._version}))
        return self._version

    def _fetch_json(self, url: str, cache_name: str) -> dict:
        """Fetch JSON from URL with local file caching."""
        cache_file = self.cache_dir / cache_name
        if cache_file.exists():
            return json.loads(cache_file.read_text())

        resp = httpx.get(url)
        resp.raise_for_status()
        data = resp.json()
        cache_file.write_text(json.dumps(data))
        return data

    def get_champions(self) -> dict[str, ChampionData]:
        """Download and parse champion data from Data Dragon CDN."""
        version = self.get_latest_version()
        url = f"{DDRAGON_BASE}/cdn/{version}/data/en_US/champion.json"
        raw = self._fetch_json(url, f"champions_{version}.json")

        champions: dict[str, ChampionData] = {}
        for champ_id, champ_data in raw["data"].items():
            champions[champ_id] = ChampionData(
                id=champ_data["id"],
                key=int(champ_data["key"]),
                name=champ_data["name"],
                title=champ_data["title"],
                tags=champ_data.get("tags", []),
            )
        return champions

    def get_items(self) -> dict[int, ItemData]:
        """Download and parse item data from Data Dragon CDN."""
        version = self.get_latest_version()
        url = f"{DDRAGON_BASE}/cdn/{version}/data/en_US/item.json"
        raw = self._fetch_json(url, f"items_{version}.json")

        items: dict[int, ItemData] = {}
        for item_id_str, item_data in raw["data"].items():
            item_id = int(item_id_str)
            gold = item_data.get("gold", {})
            items[item_id] = ItemData(
                id=item_id,
                name=item_data["name"],
                description=item_data.get("description", ""),
                gold_total=gold.get("total", 0),
                gold_base=gold.get("base", 0),
                from_items=[int(x) for x in item_data.get("from", [])],
                into_items=[int(x) for x in item_data.get("into", [])],
                stats=item_data.get("stats", {}),
            )
        return items
