from __future__ import annotations
import logging
from dataclasses import dataclass

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound

logger = logging.getLogger(__name__)


@dataclass
class TranscriptSegment:
    start: float  # seconds
    duration: float  # seconds
    text: str

    @property
    def end(self) -> float:
        return self.start + self.duration


class TranscriptFetcher:
    PREFERRED_LANGUAGES = ["ja", "en"]

    def __init__(self):
        self.api = YouTubeTranscriptApi()

    def fetch(self, video_id: str) -> list[TranscriptSegment]:
        """Fetch transcript/subtitles for a YouTube video."""
        try:
            transcript_list = self.api.list(video_id)

            # Try manually created transcripts first
            try:
                transcript = transcript_list.find_manually_created_transcript(
                    self.PREFERRED_LANGUAGES
                )
            except NoTranscriptFound:
                # Fall back to auto-generated
                try:
                    transcript = transcript_list.find_generated_transcript(
                        self.PREFERRED_LANGUAGES
                    )
                except NoTranscriptFound:
                    logger.warning(f"No transcript found for video {video_id}")
                    return []

            entries = transcript.fetch()
            return [
                TranscriptSegment(
                    start=entry["start"],
                    duration=entry["duration"],
                    text=entry["text"],
                )
                for entry in entries
            ]

        except TranscriptsDisabled:
            logger.warning(f"Transcripts disabled for video {video_id}")
            return []
        except Exception as e:
            logger.warning(f"Failed to fetch transcript: {e}")
            return []

    def get_text_at_time(self, segments: list[TranscriptSegment], time_seconds: float) -> str | None:
        """Get transcript text at a specific timestamp."""
        for seg in segments:
            if seg.start <= time_seconds <= seg.end:
                return seg.text
        return None
