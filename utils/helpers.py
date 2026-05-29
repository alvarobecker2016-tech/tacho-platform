# =========================================================
# utils/helpers.py
# ENTERPRISE DATE RECONSTRUCTION ENGINE
# =========================================================

import re
import logging
import hashlib
import uuid
from datetime import datetime, timezone, timedelta
from typing import List

from models.domain import OCRTimelineEvent, TimelineEvent

logger = logging.getLogger(__name__)

def mask_sensitive_data(text: str) -> str:
    """Maskowanie danych wrażliwych."""
    if not text:
        return ""
    text_str = str(text).strip()
    if len(text_str) <= 4:
        return "***"
    return text_str[:2] + "***"

def generate_integrity_hash(start_time, end_time, activity, duration):
    """Kryptograficzny podpis dowodu naruszenia."""
    payload = f"{start_time}{end_time}{activity}{duration}"
    return hashlib.sha256(payload.encode()).hexdigest()

class DateTimeReconstructor:
    """Pancerny parser OCR dla tachografów."""
    
    DATE_PATTERNS = [
        r"(\d{2}\.\d{2}\.\d{4})",
        r"(\d{2}/\d{2}/\d{4})",
        r"(\d{4}-\d{2}-\d{2})",
    ]

    DATE_FORMATS = [
        "%d.%m.%Y",
        "%d/%m/%Y",
        "%Y-%m-%d",
    ]

    @classmethod
    def extract_clean_date(cls, raw_date: str) -> datetime:
        if not raw_date:
            raise ValueError("Empty document date")

        raw_date = str(raw_date).strip()
        logger.info(f"RAW OCR DATE => [{raw_date}]")

        raw_date = raw_date.replace("\n", " ").replace("\r", " ")
        raw_date = re.sub(r"\s+", " ", raw_date)

        for pattern in cls.DATE_PATTERNS:
            match = re.search(pattern, raw_date)
            if match:
                clean_date = match.group(1)
                logger.info(f"CLEAN DATE => [{clean_date}]")
                for fmt in cls.DATE_FORMATS:
                    try:
                        parsed = datetime.strptime(clean_date, fmt)
                        return parsed.replace(tzinfo=timezone.utc, hour=0, minute=0, second=0, microsecond=0)
                    except ValueError:
                        continue
        
        raise ValueError(f"Cannot parse OCR date: {raw_date}")

    @classmethod
    def reconstruct(cls, document_date: str, raw_events: List) -> List[TimelineEvent]:
        try:
            current_date = cls.extract_clean_date(document_date)
        except Exception as e:
            logger.error(f"DATE PARSE ERROR: {e}")
            # Fallback na wczoraj, jeśli OCR wypluł kompletną bzdurę
            current_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)

        reconstructed_events = []
        previous_start = None

        # Sortowanie (jeśli OCR zwrócił zdarzenia nie po kolei)
        try:
            raw_events = sorted(raw_events, key=lambda e: getattr(e, 'start_time_raw', '00:00'))
        except Exception:
            pass

        for idx, raw_event in enumerate(raw_events):
            try:
                start_raw = getattr(raw_event, 'start_time_raw', None)
                end_raw = getattr(raw_event, 'end_time_raw', None)
                activity = getattr(raw_event, 'activity', 'UNKNOWN')
                confidence = getattr(raw_event, 'confidence', 1.0)

                if not start_raw or not end_raw:
                    continue

                sh, sm = map(int, start_raw.split(":"))
                eh, em = map(int, end_raw.split(":"))

                if sh > 23 or sm > 59 or eh > 23 or em > 59:
                    continue

                start_dt = current_date.replace(hour=sh, minute=sm)
                end_dt = current_date.replace(hour=eh, minute=em)

                # Przejście przez północ
                if previous_start and start_dt < previous_start:
                    current_date += timedelta(days=1)
                    start_dt += timedelta(days=1)
                    end_dt += timedelta(days=1)

                if end_dt < start_dt:
                    end_dt += timedelta(days=1)

                duration = int((end_dt - start_dt).total_seconds() / 60)
                if duration < 0 or duration > 1440:
                    continue

                integrity_hash = generate_integrity_hash(start_dt, end_dt, activity, duration)

                reconstructed_events.append(
                    TimelineEvent(
                        event_id=f"evt_{idx}_{str(uuid.uuid4())[:8]}",
                        integrity_hash=integrity_hash,
                        start_time_utc=start_dt,
                        end_time_utc=end_dt,
                        activity=activity,
                        duration_minutes=duration,
                        source="OCR_ENGINE",
                        confidence=confidence,
                        created_at=datetime.now(timezone.utc)
                    )
                )
                previous_start = start_dt

            except Exception as e:
                logger.warning(f"EVENT RECONSTRUCTION ERROR: {e}")

        logger.info(f"TIMELINE RECONSTRUCTED: {len(reconstructed_events)} events")
        return reconstructed_events
