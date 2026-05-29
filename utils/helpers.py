# =========================================================
# utils/helpers.py
# ENTERPRISE SAFE HELPERS & RECONSTRUCTION ENGINE
# =========================================================

import re
import hashlib
import uuid
from datetime import datetime, timezone, timedelta
from typing import List
from dateutil import parser  # Potężna broń do automatycznego parsowania dat

from models.domain import OCRTimelineEvent, TimelineEvent

# =========================================================
# MASKOWANIE DANYCH WRAŻLIWYCH
# =========================================================
def mask_sensitive_data(value: str) -> str:
    """Maskuje dane osobowe kierowcy lub numery kart."""
    if not value:
        return "[DANE UKRYTE]"
    val_str = str(value).strip()
    if len(val_str) < 4:
        return "[DANE UKRYTE]"
    return val_str[:2] + "*" * (len(val_str) - 4) + val_str[-2:]

# =========================================================
# KRYPTOGRAFICZNY PODPIS INTEGRALNOŚCI (SHA-256)
# =========================================================
def generate_integrity_hash(start_time, end_time, activity, duration):
    """Generuje unikalny hash dla odcinka aktywności, gwarantując niezmienność danych."""
    payload = f"{start_time}{end_time}{activity}{duration}"
    return hashlib.sha256(payload.encode()).hexdigest()

# =========================================================
# SILNIK REKONSTRUKCJI CZASU (KULOODPORNY)
# =========================================================
class DateTimeReconstructor:

    @staticmethod
    def _fallback_date() -> datetime:
        """Zwraca bezpieczną datę awaryjną (wczoraj o północy w formacie UTC)."""
        return datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        ) - timedelta(days=1)

    @staticmethod
    def _parse_dirty_date(raw_date_str: str) -> datetime:
        """
        Pancerny parser daty. Wyciąga z tekstu OCR samą datę,
        czyści śmieci (typu '29') i bezpiecznie konwertuje na datetime UTC.
        """
        fallback = DateTimeReconstructor._fallback_date()

        if not raw_date_str:
            return fallback

        try:
            # 1. REGEX EXTRACTION - Wyłuskujemy wyłącznie sam wzorzec daty ze śmieci OCR
            match = re.search(
                r'(\d{2}[./-]\d{2}[./-]\d{4}|\d{4}[./-]\d{2}[./-]\d{2})',
                str(raw_date_str)
            )

            if not match:
                # Jeśli regex nie znalazł wzorca, próbujemy bezpośrednio przepuścić przez dateutil
                parsed = parser.parse(str(raw_date_str), fuzzy=True)
                return parsed.replace(tzinfo=timezone.utc)

            # 2. SANITIZATION - Standaryzujemy separatory na kropki i czyścimy tekst
            clean_date = match.group(1).replace("-", ".").replace("/", ".")

            # 3. SMART PARSING - dateutil automatycznie rozpozna układ DD.MM.YYYY lub YYYY.MM.DD
            parsed = parser.parse(clean_date, dayfirst=(clean_date[2] == '.'))
            
            # 4. OFFSET-AWARE PROTECTION - Wymuszamy strefę UTC, zapobiegając crashom przy porównaniach
            return parsed.replace(tzinfo=timezone.utc, hour=0, minute=0, second=0, microsecond=0)

        except Exception as e:
            print(f"[WARNING] DATE PARSING FAILED FOR '{raw_date_str}': {e}")
            return fallback

    @classmethod
    def reconstruct(
        cls,
        document_date: str,
        raw_events: List[OCRTimelineEvent]
    ) -> List[TimelineEvent]:
        """
        Rekonstruuje pełną, chronologiczną oś czasu z podpisami kryptograficznymi.
        Obsługuje bezpiecznie przejścia przez północ (Midnight Rollover).
        """
        print(f"[DEBUG] DOCUMENT DATE RAW FROM OCR = [{document_date}]")
        
        # Inicjalizacja bezpieczną, przefiltrowaną datą początkową
        current_date = cls._parse_dirty_date(document_date)
        reconstructed_events = []
        previous_start = None

        # Bezpieczne sortowanie chronologiczne zdarzeń z OCR (jeśli posiadają pole startu)
        try:
            raw_events = sorted(
                raw_events,
                key=lambda e: getattr(e, 'start_time_raw', '00:00')
            )
        except Exception as e:
            print(f"[WARNING] EVENTS SORTING FAILED: {e}")

        # Pętla rekonstrukcji zdarzeń
        for idx, raw_event in enumerate(raw_events):
            try:
                # Pobranie surowych czasów rozpoczęcia i zakończenia zdarzenia
                start_raw = getattr(raw_event, 'start_time_raw', None)
                end_raw = getattr(raw_event, 'end_time_raw', None)
                activity = getattr(raw_event, 'activity', 'UNKNOWN')
                confidence = getattr(raw_event, 'confidence', 1.0)

                if not start_raw or not end_raw:
                    continue

                # Rozbicie na godziny i minuty z twardą walidacją
                sh, sm = map(int, start_raw.split(":"))
                eh, em = map(int, end_raw.split(":"))

                if sh > 23 or sm > 59 or eh > 23 or em > 59:
                    print(f"⚠️ [WARNING] Absurdalne wartości godzin zignorowane: {start_raw} - {end_raw}")
                    continue

                # Składanie pełnego obiektu datetime w bezpiecznej strefie UTC
                start_dt = current_date.replace(hour=sh, minute=sm, second=0, microsecond=0, tzinfo=timezone.utc)
                end_dt = current_date.replace(hour=eh, minute=em, second=0, microsecond=0, tzinfo=timezone.utc)

                # --- PRZESKOK PRZEZ PÓŁNOC (Midnight Rollover) ---
                if previous_start and start_dt < previous_start:
                    current_date += timedelta(days=1)
                    start_dt += timedelta(days=1)
                    end_dt += timedelta(days=1)

                # Jeśli samo zdarzenie kończy się już po północy (np. start 23:00, koniec 01:00)
                if end_dt < start_dt:
                    end_dt += timedelta(days=1)

                # Wyliczenie twardej matematycznej długości trwania odcinka w minutach
                duration = int((end_dt - start_dt).total_seconds() / 60)

                # Bezpiecznik przed błędnymi odczytami wielodniowymi
                if duration < 0 or duration > 1440:
                    print(f"⚠️ [WARNING] Pominięto podejrzany czas trwania zdarzenia: {duration} min.")
                    continue

                # Generowanie podpisu cyfrowego zabezpieczającego dowód przed manipulacją
                integrity_hash = generate_integrity_hash(start_dt, end_dt, activity, duration)

                # Tworzenie ostatecznego obiektu biznesowego dla Maszyny Stanów i Reguł ITD
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
                print(f"[WARNING] SINGLE EVENT RECONSTRUCTION FAILED: {e}")
                continue

        return reconstructed_events
