from enum import Enum

class EventType(str, Enum):
    DRIVING = "DRIVING"
    BREAK = "BREAK"
    REST = "REST"
    OTHER_WORK = "OTHER_WORK"
    AVAILABILITY = "AVAILABILITY"
    UNKNOWN = "UNKNOWN"
