from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path

import cv2

from ..video.ocr_engine import OCREngine
from .stream_capture import StreamCapture
from .game_state import GameStateTracker
from .event_detector import LiveEventDetector
from .commentary_llm import CommentaryLLM
from .live_output import (
    CommentaryEntry,
    LiveTerminalOutput,
    TextFileOutput,
)

logger = logging.getLogger(__name__)


class LiveRunner:
    """Main asyncio loop that ties all live components together."""

    def __init__(
        self,
        url: str,
        api_key: str,
        output_file: Path | None = None,
        interval: float = 1.0,
        min_significance: float = 0.3,
        start_time: float = 0.0,
    ) -> None:
        self._url = url
        self._api_key = api_key
        self._output_file = output_file
        self._interval = interval
        self._min_significance = min_significance
        self._start_time = start_time
        self._running = False

    async def run(self) -> None:
        """Run the live commentary loop. Stops on Ctrl+C or end of video."""
        capture = StreamCapture(self._url)
        capture.start()

        width, height = capture.resolution
        ocr = OCREngine()
        tracker = GameStateTracker(ocr, width, height)
        detector = LiveEventDetector()
        llm = CommentaryLLM(self._api_key)
        terminal = LiveTerminalOutput()
        file_out = TextFileOutput(self._output_file) if self._output_file else None

        # Detect if this is a VOD (has finite frame count)
        total_frames = capture._cap.get(cv2.CAP_PROP_FRAME_COUNT) if capture._cap else 0
        fps = capture._cap.get(cv2.CAP_PROP_FPS) if capture._cap else 30
        is_vod = total_frames > 0
        skip_frames = max(1, int(fps * self._interval)) if is_vod else 1

        if is_vod:
            duration = total_frames / fps if fps > 0 else 0
            logger.info("VOD detected: %.0fs, %.0f fps, skipping %d frames per step", duration, fps, skip_frames)

            # Skip to start time if specified
            if self._start_time > 0 and capture._cap:
                start_frame = int(self._start_time * fps)
                capture._cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
                logger.info("Skipped to %.0fs (frame %d)", self._start_time, start_frame)

        self._running = True
        terminal.start()
        no_frame_count = 0

        try:
            while self._running:
                # For VODs, skip frames to match the desired interval
                if is_vod and skip_frames > 1:
                    for _ in range(skip_frames - 1):
                        if capture._cap:
                            capture._cap.grab()

                frame = capture.read_frame()
                if frame is None:
                    no_frame_count += 1
                    if is_vod or no_frame_count > 10:
                        logger.info("End of stream/video")
                        break
                    await asyncio.sleep(self._interval)
                    continue
                no_frame_count = 0

                # Detect state changes (OCR only runs on changed regions)
                changes = tracker.update(frame.frame)

                # Update terminal display with current state
                terminal.update_state(tracker.state)

                if not changes:
                    if not is_vod:
                        await asyncio.sleep(self._interval)
                    continue

                # Detect events from state changes
                events = detector.detect(changes, tracker.state)

                for event in events:
                    if event.significance < self._min_significance:
                        continue

                    # Always show the basic event description
                    entry = CommentaryEntry(
                        game_time=event.game_time,
                        message=event.description,
                        significance=event.significance,
                    )
                    terminal.add_commentary(entry)
                    if file_out:
                        file_out.write(entry)

                    # Generate AI commentary for significant events
                    commentary = await llm.generate(event, tracker.state, [])
                    if commentary:
                        ai_entry = CommentaryEntry(
                            game_time=event.game_time,
                            message=commentary,
                            significance=event.significance,
                        )
                        terminal.add_commentary(ai_entry)
                        if file_out:
                            file_out.write(ai_entry)

                if not is_vod:
                    await asyncio.sleep(self._interval)

        except (KeyboardInterrupt, asyncio.CancelledError):
            logger.info("Stopping live commentary...")
        finally:
            self._running = False
            terminal.stop()
            capture.stop()

    def stop(self) -> None:
        self._running = False
