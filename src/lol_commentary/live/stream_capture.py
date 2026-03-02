from __future__ import annotations

import logging
from dataclasses import dataclass

import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class CapturedFrame:
    """A single frame captured from a live stream or video."""
    timestamp: float  # seconds (POS_MSEC for video, wall-clock for live)
    frame: np.ndarray  # BGR image


class StreamCapture:
    """Capture frames from a live stream or video.

    Resolution order:
    1. streamlink (YouTube Live / Twitch)
    2. yt-dlp (YouTube VOD / any yt-dlp-supported URL)
    3. Direct cv2.VideoCapture (local file or raw URL)
    """

    def __init__(self, url: str) -> None:
        self._url = url
        self._cap: cv2.VideoCapture | None = None
        self._width = 0
        self._height = 0

    def start(self) -> None:
        """Resolve the URL and open with cv2.VideoCapture."""
        stream_url = self._resolve_url()

        self._cap = cv2.VideoCapture(stream_url)
        if not self._cap.isOpened():
            raise RuntimeError(f"Failed to open video: {stream_url}")

        self._width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self._height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        logger.info("Capture opened: %dx%d", self._width, self._height)

    def _resolve_url(self) -> str:
        """Try multiple methods to resolve the URL to a playable stream.

        Order: yt-dlp first (better quality control), then streamlink
        (better for live streams), then direct URL.
        """
        # 1. Try yt-dlp first (reliable quality selection for VOD and live)
        try:
            import yt_dlp
            logger.info("Trying yt-dlp: %s", self._url)
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                # Prefer 720p video-only for OCR quality (cv2 doesn't need audio)
                "format": "bestvideo[height=720]/bestvideo[height<=1080]/bestvideo/best",
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self._url, download=False)
                url = info.get("url")
                if url:
                    logger.info("yt-dlp resolved: %sp %s", info.get("height", "?"), info.get("ext", "?"))
                    return url
                raise RuntimeError("yt-dlp returned no URL")
        except Exception as e:
            logger.info("yt-dlp failed: %s", e)

        # 2. Try streamlink (good for live streams)
        try:
            import streamlink
            logger.info("Trying streamlink: %s", self._url)
            streams = streamlink.streams(self._url)
            if streams:
                quality = "720p" if "720p" in streams else "best"
                url = streams[quality].url
                logger.info("streamlink resolved (%s)", quality)
                return url
        except Exception as e:
            logger.info("streamlink failed: %s", e)

        # 3. Assume it's a direct URL or local file path
        logger.info("Using URL directly: %s", self._url)
        return self._url

    def read_frame(self) -> CapturedFrame | None:
        """Read the next frame."""
        if self._cap is None:
            return None

        ret, frame = self._cap.read()
        if not ret:
            return None

        return CapturedFrame(
            timestamp=self._cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0,
            frame=frame,
        )

    def stop(self) -> None:
        """Release the video capture."""
        if self._cap is not None:
            self._cap.release()
            self._cap = None
            logger.info("Capture stopped")

    @property
    def resolution(self) -> tuple[int, int]:
        return (self._width, self._height)

    def __enter__(self) -> StreamCapture:
        self.start()
        return self

    def __exit__(self, *args) -> None:
        self.stop()
