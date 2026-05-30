import re
from datetime import datetime, timedelta, timezone
from typing import List, Tuple
from domain.enums import EventType
from ocr.transcriber import OCRTimelineEvent

class TimelineReconstructor:
    
    def parse_time(self, raw: str) -> Tuple[int, int]:
        clean = str(raw).lower().replace("h", ":").replace("m", "").strip()
        if ":" in clean:
            h, m = clean.split(":", 1)
            try: return int(h), int(m)
            except: return 0, 0
        return 0, 0

    def map_pictogram_to_type(self, pic: str) -> EventType:
        char = str(pic).strip().lower()
        if any(x in char for x in ['h', 'bed', 'rest']): return EventType.REST
        if any(x in char for x in ['*', 'work', 'x']): return EventType.OTHER_WORK
        if any(x in char for x in ['o', 'driving', '0']): return EventType.DRIVING
        return EventType.UNKNOWN

    def process(self, doc_date: str, raw_events: List[OCRTimelineEvent]):
        date_obj = datetime.strptime(re.search(r"(\d{2}[./-]\d{2}[./-]\d{4})", doc_date).group(1).replace("-", "."), "%d.%m.%Y").replace(tzinfo=timezone.utc)
        
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
                events.append({
                    "start": s_dt, "end": e_dt, "duration": dur, "activity": act_type
                })
            prev_start = s_dt
            
        return events
