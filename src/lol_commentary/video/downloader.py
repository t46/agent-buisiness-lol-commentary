from __future__ import annotations
import logging
import re
from dataclasses import dataclass
from pathlib import Path

import yt_dlp

logger = logging.getLogger(__name__)


@dataclass
class VideoInfo:
    url: str
    video_id: str
    title: str
    upload_date: str  # YYYYMMDD format
    duration: int  # seconds
    filepath: Path | None = None
    channel: str = ""
    description: str = ""


class VideoDownloader:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def extract_info(self, url: str) -> VideoInfo:
        """Extract video metadata without downloading."""
        ydl_opts = {"quiet": True, "no_warnings": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return VideoInfo(
                url=url,
                video_id=info["id"],
                title=info.get("title", ""),
                upload_date=info.get("upload_date", ""),
                duration=info.get("duration", 0),
                channel=info.get("channel", ""),
                description=info.get("description", ""),
            )

    def download(self, url: str, resolution: str = "1080") -> VideoInfo:
        """Download video at specified resolution."""
        info = self.extract_info(url)
        output_path = self.output_dir / f"{info.video_id}.mp4"

        if output_path.exists():
            logger.info(f"Video already downloaded: {output_path}")
            info.filepath = output_path
            return info

        ydl_opts = {
            "format": f"bestvideo[height<={resolution}]+bestaudio/best[height<={resolution}]",
            "outtmpl": str(output_path),
            "merge_output_format": "mp4",
            "quiet": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        info.filepath = output_path
        return info

    @staticmethod
    def parse_player_names_from_title(title: str) -> list[str]:
        """Attempt to extract player names from video title.

        Common patterns:
        - "Player1 vs Player2"
        - "Team1 vs Team2"
        - "Player1 - Champion gameplay"
        """
        names = []
        # Pattern: "X vs Y"
        vs_match = re.search(r'(\S+)\s+vs\.?\s+(\S+)', title, re.IGNORECASE)
        if vs_match:
            names.extend([vs_match.group(1), vs_match.group(2)])
        return names
