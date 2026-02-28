from __future__ import annotations
from dataclasses import dataclass, field

from ..riot_api.models import TimelineEvent


@dataclass
class GameSegment:
    start_time: int  # ms
    end_time: int  # ms
    events: list[TimelineEvent] = field(default_factory=list)
    segment_type: str = "event"  # event, teamfight, macro, laning
    importance: float = 0.0

    @property
    def duration_seconds(self) -> float:
        return (self.end_time - self.start_time) / 1000

    @property
    def game_time_str(self) -> str:
        total_secs = self.start_time // 1000
        return f"{total_secs // 60}:{total_secs % 60:02d}"


class GameSegmenter:
    TEAMFIGHT_WINDOW_MS = 15_000  # 15 seconds
    EVENT_WINDOW_MS = 30_000  # 30 seconds
    MACRO_INTERVAL_MS = 120_000  # 2 minutes
    KILL_EVENTS = {"CHAMPION_KILL"}

    def segment(self, events: list[TimelineEvent], game_duration_ms: int) -> list[GameSegment]:
        """Segment the game into commentary-worthy intervals."""
        segments = []

        # Separate kill events for teamfight clustering
        kill_events = [e for e in events if e.type in self.KILL_EVENTS]
        other_important = [e for e in events if e.type in {
            "ELITE_MONSTER_KILL", "BUILDING_KILL"
        }]

        # Cluster kills into teamfights
        teamfight_segments = self._cluster_teamfights(kill_events)
        segments.extend(teamfight_segments)

        # Add objective events as individual segments
        for event in other_important:
            if not self._overlaps_existing(event.timestamp, segments):
                segments.append(GameSegment(
                    start_time=max(0, event.timestamp - self.EVENT_WINDOW_MS // 2),
                    end_time=event.timestamp + self.EVENT_WINDOW_MS // 2,
                    events=[event],
                    segment_type="event",
                ))

        # Fill gaps with macro segments
        segments.sort(key=lambda s: s.start_time)
        macro_segments = self._fill_macro_gaps(segments, game_duration_ms)
        segments.extend(macro_segments)

        segments.sort(key=lambda s: s.start_time)
        return segments

    def _cluster_teamfights(self, kill_events: list[TimelineEvent]) -> list[GameSegment]:
        """Group kills within 15s windows into teamfight segments."""
        if not kill_events:
            return []

        clusters: list[list[TimelineEvent]] = []
        current_cluster = [kill_events[0]]

        for event in kill_events[1:]:
            if event.timestamp - current_cluster[-1].timestamp <= self.TEAMFIGHT_WINDOW_MS:
                current_cluster.append(event)
            else:
                clusters.append(current_cluster)
                current_cluster = [event]
        clusters.append(current_cluster)

        segments = []
        for cluster in clusters:
            is_teamfight = len(cluster) >= 3
            segment_type = "teamfight" if is_teamfight else "event"
            start = cluster[0].timestamp
            end = cluster[-1].timestamp
            segments.append(GameSegment(
                start_time=max(0, start - self.EVENT_WINDOW_MS // 2),
                end_time=end + self.EVENT_WINDOW_MS // 2,
                events=cluster,
                segment_type=segment_type,
            ))
        return segments

    def _overlaps_existing(self, timestamp: int, segments: list[GameSegment]) -> bool:
        for seg in segments:
            if seg.start_time <= timestamp <= seg.end_time:
                return True
        return False

    def _fill_macro_gaps(self, segments: list[GameSegment], game_duration_ms: int) -> list[GameSegment]:
        """Add macro commentary segments during quiet periods."""
        macro_segments = []
        covered = set()
        for seg in segments:
            for t in range(seg.start_time // self.MACRO_INTERVAL_MS,
                          seg.end_time // self.MACRO_INTERVAL_MS + 1):
                covered.add(t)

        for i in range(game_duration_ms // self.MACRO_INTERVAL_MS + 1):
            if i not in covered:
                start = i * self.MACRO_INTERVAL_MS
                end = min(start + self.MACRO_INTERVAL_MS, game_duration_ms)
                macro_segments.append(GameSegment(
                    start_time=start,
                    end_time=end,
                    segment_type="macro",
                ))
        return macro_segments
