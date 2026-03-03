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
    ANTHROPIC_API_KEY: str = ""
    LIVE_CAPTURE_INTERVAL: float = 1.0
    LIVE_COMMENTARY_COOLDOWN: float = 10.0
    LIVE_MIN_SIGNIFICANCE: float = 0.3
    # Overlay settings
    OVERLAY_HOST: str = "127.0.0.1"
    OVERLAY_PORT: int = 8765
    COMMENTARY_MIN_INTERVAL: float = 8.0
    COMMENTARY_FILL_INTERVAL: float = 30.0
    DEFAULT_PERSONA: str = "kenshi"


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
        ANTHROPIC_API_KEY=os.getenv("ANTHROPIC_API_KEY", ""),
        LIVE_CAPTURE_INTERVAL=float(os.getenv("LIVE_CAPTURE_INTERVAL", "1.0")),
        LIVE_COMMENTARY_COOLDOWN=float(os.getenv("LIVE_COMMENTARY_COOLDOWN", "10.0")),
        LIVE_MIN_SIGNIFICANCE=float(os.getenv("LIVE_MIN_SIGNIFICANCE", "0.3")),
        OVERLAY_HOST=os.getenv("OVERLAY_HOST", "127.0.0.1"),
        OVERLAY_PORT=int(os.getenv("OVERLAY_PORT", "8765")),
        COMMENTARY_MIN_INTERVAL=float(os.getenv("COMMENTARY_MIN_INTERVAL", "8.0")),
        COMMENTARY_FILL_INTERVAL=float(os.getenv("COMMENTARY_FILL_INTERVAL", "30.0")),
        DEFAULT_PERSONA=os.getenv("DEFAULT_PERSONA", "kenshi"),
    )

    _settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    _settings.CACHE_DIR.mkdir(parents=True, exist_ok=True)

    return _settings
