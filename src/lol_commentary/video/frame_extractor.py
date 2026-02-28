from __future__ import annotations
import logging
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from .hud_regions import Region, SpectatorHUD

logger = logging.getLogger(__name__)


@dataclass
class ExtractedFrame:
    timestamp: float  # seconds
    frame: np.ndarray  # BGR image
    frame_number: int


class FrameExtractor:
    def __init__(self, video_path: Path):
        self.video_path = video_path
        self.cap = cv2.VideoCapture(str(video_path))
        if not self.cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.duration = self.total_frames / self.fps if self.fps > 0 else 0

    def extract_at_intervals(
        self,
        interval_seconds: float = 5.0,
        start_time: float = 0.0,
        end_time: float | None = None,
    ) -> list[ExtractedFrame]:
        """Extract frames at regular intervals."""
        if end_time is None:
            end_time = self.duration

        frames = []
        current_time = start_time
        while current_time <= end_time:
            frame = self.extract_at_time(current_time)
            if frame is not None:
                frames.append(frame)
            current_time += interval_seconds
        return frames

    def extract_at_time(self, time_seconds: float) -> ExtractedFrame | None:
        """Extract a single frame at a specific timestamp."""
        frame_number = int(time_seconds * self.fps)
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = self.cap.read()
        if not ret:
            return None
        return ExtractedFrame(
            timestamp=time_seconds,
            frame=frame,
            frame_number=frame_number,
        )

    def extract_dense(
        self,
        center_time: float,
        window_seconds: float = 15.0,
        interval_seconds: float = 1.0,
    ) -> list[ExtractedFrame]:
        """Extract frames densely around an event."""
        start = max(0, center_time - window_seconds / 2)
        end = min(self.duration, center_time + window_seconds / 2)
        return self.extract_at_intervals(interval_seconds, start, end)

    def crop_region(self, frame: np.ndarray, region: Region) -> np.ndarray:
        """Crop a specific HUD region from a frame."""
        y_slice, x_slice = region.to_slice()
        return frame[y_slice, x_slice].copy()

    def get_hud_regions(self, frame: np.ndarray) -> dict[str, np.ndarray | list[np.ndarray]]:
        """Extract all HUD regions from a frame."""
        regions = SpectatorHUD.get_scaled_regions(self.width, self.height)
        result = {}
        for key, region in regions.items():
            if isinstance(region, list):
                result[key] = [self.crop_region(frame, r) for r in region]
            else:
                result[key] = self.crop_region(frame, region)
        return result

    def close(self):
        self.cap.release()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
