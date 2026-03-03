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
from .commentary_scheduler import CommentaryScheduler
from .live_output import (
    CommentaryEntry,
    LiveTerminalOutput,
    TextFileOutput,
)
from .persona import Persona, get_persona

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
        persona_id: str | None = None,
        overlay_port: int = 8765,
        overlay_host: str = "127.0.0.1",
        enable_overlay: bool = False,
        min_interval: float = 8.0,
        fill_interval: float = 30.0,
    ) -> None:
        self._url = url
        self._api_key = api_key
        self._output_file = output_file
        self._interval = interval
        self._min_significance = min_significance
        self._start_time = start_time
        self._enable_overlay = enable_overlay
        self._overlay_port = overlay_port
        self._overlay_host = overlay_host
        self._min_interval = min_interval
        self._fill_interval = fill_interval
        self._running = False

        # Load persona
        self._persona: Persona | None = None
        if persona_id:
            try:
                self._persona = get_persona(persona_id)
            except KeyError:
                logger.warning("Persona '%s' not found, using default", persona_id)

    async def run(self) -> None:
        """Run the live commentary loop. Stops on Ctrl+C or end of video."""
        capture = StreamCapture(self._url)
        capture.start()

        width, height = capture.resolution
        ocr = OCREngine()
        tracker = GameStateTracker(ocr, width, height)
        detector = LiveEventDetector()
        llm = CommentaryLLM(self._api_key, persona=self._persona)
        scheduler = CommentaryScheduler(
            min_interval=self._min_interval,
            fill_interval=self._fill_interval,
        )
        terminal = LiveTerminalOutput()
        file_out = TextFileOutput(self._output_file) if self._output_file else None

        # Start overlay server if enabled
        overlay = None
        if self._enable_overlay:
            from .overlay_server import OverlayServer
            persona = self._persona or get_persona("kenshi")
            overlay = OverlayServer(
                persona=persona,
                host=self._overlay_host,
                port=self._overlay_port,
            )
            await overlay.start()
            logger.info(
                "Overlay: http://%s:%d", self._overlay_host, self._overlay_port
            )

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
                # --- Process scheduled comments ---
                ready = scheduler.next_ready()
                if ready:
                    if ready.comment_type == "fill":
                        # Generate fill commentary
                        fill_text = await llm.generate_fill(tracker.state)
                        if fill_text:
                            fill_entry = CommentaryEntry(
                                game_time=ready.game_time,
                                message=fill_text,
                                significance=0.2,
                            )
                            terminal.add_commentary(fill_entry)
                            if file_out:
                                file_out.write(fill_entry)
                            if overlay:
                                await overlay.add_commentary(
                                    fill_text, 0.2,
                                )
                    elif ready.event:
                        # Generate event commentary
                        commentary = await llm.generate(
                            ready.event, tracker.state, []
                        )
                        if commentary:
                            ai_entry = CommentaryEntry(
                                game_time=ready.event.game_time,
                                message=commentary,
                                significance=ready.event.significance,
                            )
                            terminal.add_commentary(ai_entry)
                            if file_out:
                                file_out.write(ai_entry)
                            if overlay:
                                await overlay.add_commentary(
                                    commentary, ready.event.significance,
                                )

                # --- Check if fill is needed ---
                if scheduler.should_fill():
                    fill_req = scheduler.create_fill_request(tracker.state)
                    fill_text = await llm.generate_fill(tracker.state)
                    if fill_text:
                        fill_entry = CommentaryEntry(
                            game_time=fill_req.game_time,
                            message=fill_text,
                            significance=0.2,
                        )
                        terminal.add_commentary(fill_entry)
                        if file_out:
                            file_out.write(fill_entry)
                        if overlay:
                            await overlay.add_commentary(fill_text, 0.2)

                # --- Capture and process frame ---
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

                # Update terminal and overlay with current state
                terminal.update_state(tracker.state)
                if overlay:
                    await overlay.update_state(tracker.state)

                if not changes:
                    if not is_vod:
                        await asyncio.sleep(self._interval)
                    continue

                # Detect events from state changes
                events = detector.detect(changes, tracker.state)

                for event in events:
                    if event.significance < self._min_significance:
                        continue

                    # Show basic event description immediately
                    entry = CommentaryEntry(
                        game_time=event.game_time,
                        message=event.description,
                        significance=event.significance,
                    )
                    terminal.add_commentary(entry)
                    if file_out:
                        file_out.write(entry)

                    # Enqueue for AI commentary via scheduler
                    scheduler.enqueue(event, tracker.state)

                if not is_vod:
                    await asyncio.sleep(self._interval)

        except (KeyboardInterrupt, asyncio.CancelledError):
            logger.info("Stopping live commentary...")
        finally:
            self._running = False
            terminal.stop()
            capture.stop()
            if overlay:
                await overlay.stop()

    def stop(self) -> None:
        self._running = False
