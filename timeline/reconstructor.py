import re
from datetime import datetime, timedelta, timezone
from typing import List, Tuple
from domain.enums import EventType
from domain.models import TimelineEvent
from ocr.transcriber import OCRTimelineEvent

class TimelineReconstructor:
    
    def parse_time(self, raw: str) -> Tuple[int, int]:
        clean = str(raw).lower().replace("h", ":").replace("m", "").replace("in", "").replace(" ", "").strip()
        if clean.isdigit():
            val = int(clean)
            return (0, val) if val < 60 else (val // 60, val % 60)
        if ":" in clean:
            parts = clean.split(":", 1)
            try: return int(parts[0]), int(parts[1])
            except: return 0, 0
        return 0, 0

    def map_pictogram_to_type(self, pic: str) -> EventType:
        char = str(pic).strip().lower()
        if char in ['o', '○', '0', 'jazda', 'driving']: return EventType.DRIVING
        if char in ['*', 'x', 'młotki', 'praca', 'work', 'hammer']: return EventType.OTHER_WORK
        if char in ['h', 'łóżko', 'odpoczynek', 'pauza', 'bed', 'rest']: return EventType.REST
        if char in ['☒', 'koperta', 'dyspozycyjność', 'box', 'avail']: return EventType.AVAILABILITY
        return EventType.UNKNOWN

    def process(self, doc_date: str, raw_events: List[OCRTimelineEvent]) -> List[TimelineEvent]:
        match = re.search(r"(\d{2}[./-]\d{2}[./-]\d{4})", doc_date)
        if not match:
            date_obj = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            date_obj = datetime.strptime(match.group(1).replace("-", "."), "%d.%m.%Y").replace(tzinfo=timezone.utc)
        
        events = []
        prev_start = None
        
        for r in raw_events:
            sh, sm = self.parse_time(r.start_time_raw)
            dh, dm = self.parse_time(r.duration_raw)
            
            s_dt = date_obj.replace(hour=sh, minute=sm)
            if prev_start and s_dt < prev_start:
                s_dt += timedelta(days=1)
                date_obj += timedelta(days=1)
            
            e_dt = s_dt + timedelta(hours=dh, minutes=dm)
            act_type = self.map_pictogram_to_type(r.pictogram_raw)
            dur = int((e_dt - s_dt).total_seconds() / 60)
            
            if dur > 0:
                events.append(TimelineEvent(
                    start=s_dt,
                    end=e_dt,
                    duration=dur,
                    activity=act_type,
                    confidence=r.confidence,
                    pictogram_raw=r.pictogram_raw
                ))
            prev_start = s_dt
            
        return events
