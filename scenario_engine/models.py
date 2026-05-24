from pydantic import BaseModel, computed_field
from datetime import datetime, timedelta
from typing import List
from enum import Enum

class EventType(str, Enum):
    DRIVING = "DRIVING"
    BREAK_REST = "BREAK_REST"
    OTHER_WORK = "OTHER_WORK"
    AVAILABILITY = "AVAILABILITY"

class Event(BaseModel):
    type: EventType
    start: datetime
    end: datetime

    # To jest nasza nowa funkcja matematyczna!
    @computed_field
    @property
    def duration_minutes(self) -> int:
        delta = self.end - self.start
        return int(delta.total_seconds() / 60)

    # Formatuje czas do napisu typu "04h30m"
    def duration_formatted(self) -> str:
        hours = self.duration_minutes // 60
        minutes = self.duration_minutes % 60
        return f"{hours:02}h{minutes:02}m"

class Scenario(BaseModel):
    scenario_id: str
    driver_name: str
    events: List[Event]

    @computed_field
    @property
    def total_driving_minutes(self) -> int:
        return sum(e.duration_minutes for e in self.events if e.type == EventType.DRIVING)