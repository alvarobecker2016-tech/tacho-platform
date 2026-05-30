from domain.enums import EventType, RestType
from domain.models import TimelineEvent

class RestClassifier:
    def classify(self, event: TimelineEvent) -> RestType:
        if event.activity != EventType.REST:
            return RestType.NONE
            
        dur = event.duration
        
        if dur >= 660:
            return RestType.REGULAR_DAILY
        elif dur >= 540:
            return RestType.REDUCED_DAILY
        elif dur >= 180:
            return RestType.SPLIT_DAILY_PART
            
        return RestType.NONE
