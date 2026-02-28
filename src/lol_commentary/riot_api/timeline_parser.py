from .models import Position, TimelineEvent


class TimelineParser:
    TRACKED_EVENTS = {
        "CHAMPION_KILL",
        "ELITE_MONSTER_KILL",
        "BUILDING_KILL",
        "TURRET_PLATE_DESTROYED",
        "ITEM_PURCHASED",
        "WARD_PLACED",
        "WARD_KILL",
        "LEVEL_UP",
    }

    def parse(self, raw_timeline: dict) -> list[TimelineEvent]:
        """Parse raw match-v5 timeline into a list of TimelineEvent models."""
        events: list[TimelineEvent] = []
        for frame in raw_timeline["info"]["frames"]:
            for event in frame["events"]:
                if event["type"] in self.TRACKED_EVENTS:
                    events.append(self._parse_event(event))
        return events

    def _parse_event(self, raw: dict) -> TimelineEvent:
        """Map a raw API event dict to a TimelineEvent model."""
        position = None
        if "position" in raw:
            position = Position(x=raw["position"]["x"], y=raw["position"]["y"])

        return TimelineEvent(
            timestamp=raw["timestamp"],
            type=raw["type"],
            killer_id=raw.get("killerId"),
            victim_id=raw.get("victimId"),
            assisting_participant_ids=raw.get("assistingParticipantIds", []),
            position=position,
            monster_type=raw.get("monsterType"),
            monster_sub_type=raw.get("monsterSubType"),
            building_type=raw.get("buildingType"),
            lane_type=raw.get("laneType"),
            tower_type=raw.get("towerType"),
            item_id=raw.get("itemId"),
            participant_id=raw.get("participantId"),
            level=raw.get("level"),
            ward_type=raw.get("wardType"),
        )
