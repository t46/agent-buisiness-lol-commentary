from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv
import os


load_dotenv()


@dataclass
class Settings:
    RIOT_API_KEY: str = ""
    REGION: str = "jp1"
    PLATFORM: str = "JP1"
    DATA_DIR: Path = field(default_factory=lambda: Path("data"))
    CACHE_DIR: Path = field(default_factory=lambda: Path("data/cache"))
    CACHE_TTL: int = 86400  # 24 hours


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is not None:
        return _settings

    _settings = Settings(
        RIOT_API_KEY=os.getenv("RIOT_API_KEY", ""),
        REGION=os.getenv("REGION", "jp1"),
        PLATFORM=os.getenv("PLATFORM", "JP1"),
        DATA_DIR=Path(os.getenv("DATA_DIR", "data")),
        CACHE_DIR=Path(os.getenv("CACHE_DIR", "data/cache")),
        CACHE_TTL=int(os.getenv("CACHE_TTL", "86400")),
    )

    _settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    _settings.CACHE_DIR.mkdir(parents=True, exist_ok=True)

    return _settings
