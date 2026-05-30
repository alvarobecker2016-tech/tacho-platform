from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from domain.enums import EventType, Severity

class TimelineEvent(BaseModel):
    start: datetime
    end: datetime
    duration: int
    activity: EventType

class Violation(BaseModel):
    rule_id: str
    article: str
    regulation: str
    description: str
    explanation: str
    severity: Severity
    estimated_fine_eur: int
    defense_strategy: Optional[str] = None
    defense_possible: bool = True
