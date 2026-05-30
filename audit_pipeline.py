# =========================================================
# POCKET DGSA & TACHO
# ENTERPRISE COMPLIANCE AI ENGINE v19 - INTEGRATED
# SERVICE-ORIENTED CORE (SOA, EVIDENCE-BASED DEFENSE, DB-READY)
# =========================================================

import base64
import hashlib
import uuid
import time
import re
import logging
from abc import ABC, abstractmethod

from enum import Enum
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Tuple
from pydantic import BaseModel, Field, field_validator
from openai import OpenAI

# =========================================================
# 1. DOMAIN LAYER: CONFIG, POLICIES & ENUMS
# =========================================================

OPENAI_MODEL_VISION = "gpt-4o"
OPENAI_MODEL_FAST = "gpt-4o-mini"
CONFIDENCE_THRESHOLD = 0.80

client = OpenAI()
logger = logging.getLogger(__name__)

class ConfidencePolicy:
    OVERLAP_DECAY = 0.70
    TRUNCATION_DECAY = 0.60
    SYNTHETIC_GAP = 0.00
    MIN_CONFIDENCE = 0.10

class EventType(str, Enum):
    DRIVING = "DRIVING"
    BREAK = "BREAK"
    REST = "REST"
    OTHER_WORK = "OTHER_WORK"
    AVAILABILITY = "AVAILABILITY"
    UNKNOWN = "UNKNOWN"

class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class UnknownPolicy(str, Enum):
    STRICT = "STRICT"
    NEUTRAL = "NEUTRAL"
    DRIVER_FRIENDLY = "DRIVER_FRIENDLY"

class RestType(str, Enum):
    NONE = "NONE"
    REGULAR_DAILY = "REGULAR_DAILY"
    REDUCED_DAILY = "REDUCED_DAILY"
    SPLIT_DAILY = "SPLIT_DAILY"

# =========================================================
# 2. DOMAIN LAYER: EXTERNAL EVIDENCE & DEFENSE
# =========================================================

class ExternalEvidence(BaseModel):
    """Zewnętrzne dowody telematyczne lub zeznania kierowcy dla Art. 12."""
    traffic_jam_detected: bool = False
    accident_on_route: bool = False
    weather_alert_active: bool = False
    parking_unavailable: bool = False
    border_delay: bool = False
    ferry_or_train_crossing: bool = False

# =========================================================
# 3. DOMAIN LAYER: JURISDICTION PACKS
# =========================================================

class FineTable(BaseModel):
    base_fine_eur: int
    per_minute_excess_eur: float = 0.0
    max_fine_eur: Optional[int] = None

class JurisdictionPack(BaseModel):
    country_code: str
    authority: str
    tolerance_minutes: int
    strict_mode: bool
    unknown_policy: UnknownPolicy
    fine_tables: Dict[str, FineTable]

    def calculate_fine(self, rule_id: str, excess_minutes: int) -> int:
        if rule_id not in self.fine_tables: return 0
        table = self.fine_tables[rule_id]
        fine = table.base_fine_eur + (excess_minutes * table.per_minute_excess_eur)
        return int(min(fine, table.max_fine_eur)) if table.max_fine_eur else int(fine)

GERMANY_PACK_2025 = JurisdictionPack(
    country_code="DE", authority="BALM", tolerance_minutes=1, strict_mode=True, unknown_policy=UnknownPolicy.STRICT,
    fine_tables={
        "ART7_CONTINUOUS_DRIVING": FineTable(base_fine_eur=100, per_minute_excess_eur=2.5),
        "ART6_DAILY_DRIVING": FineTable(base_fine_eur=150, per_minute_excess_eur=3.0),
        "DATA_GAP_RULE": FineTable(base_fine_eur=250, per_minute_excess_eur=0.0)
    }
)

POLAND_PACK_2025 = JurisdictionPack(
    country_code="PL", authority="ITD", tolerance_minutes=3, strict_mode=False, unknown_policy=UnknownPolicy.NEUTRAL,
    fine_tables={
        "ART7_CONTINUOUS_DRIVING": FineTable(base_fine_eur=50, per_minute_excess_eur=1.0),
        "ART6_DAILY_DRIVING": FineTable(base_fine_eur=80, per_minute_excess_eur=1.5),
        "DATA_GAP_RULE": FineTable(base_fine_eur=100, per_minute_excess_eur=0.0)
    }
)

# =========================================================
# 4. DOMAIN LAYER: ENTITIES (DB SCHEMA PROTOTYPES)
# =========================================================

class OCRTimelineEvent(BaseModel):
    start_time_raw: str
    end_time_raw: str
    activity: EventType
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    @field_validator("activity", mode="before")
    @classmethod
    def normalize_activity(cls, value):
        mapping = {"DRIVE": "DRIVING", "WORK": "OTHER_WORK", "AVAIL": "AVAILABILITY"}
        return mapping.get(str(value).upper(), str(value).upper()) if isinstance(value, str) else value

    @field_validator("start_time_raw", "end_time_raw", mode="before")
    @classmethod
    def validate_time(cls, value):
        val = str(value).replace("h", ":").replace("H", ":").strip()
        if not re.match(r"^\d{2}:\d{2}$", val): raise ValueError(f"Invalid time format: {val}")
        return val

class TimelineEventEntity(BaseModel):
    """Odpowiada tabeli `timeline_events` w DB."""
    id: str
    audit_id: str
    driver_id: str
    integrity_hash: str
    parent_hash: str
    start_time_utc: datetime
    end_time_utc: datetime
    activity: EventType
    duration_minutes: int
    confidence: float
    is_corrected: bool = False
    correction_reason: Optional[str] = None
    created_at: datetime

class ViolationRecord(BaseModel):
    """Odpowiada tabeli `violations` w DB."""
    id: str
    audit_id: str
    rule_id: str
    article: str
    description: str
    explanation: str
    severity: Severity
    estimated_fine_eur: int
    confidence: float
    defense_score: float = 0.0
    defense_strategy: Optional[str] = None
    evidence_event_ids: List[str]

class AuditRecord(BaseModel):
    """Odpowiada tabeli `audits` w DB."""
    id: str
    driver_id: str
    created_at: datetime
    status: str
    violations: List[ViolationRecord]
    total_fine_eur: int
    timeline_confidence: float

# =========================================================
# 5. REPOSITORY LAYER
# =========================================================

class TimelineRepository(ABC):
    @abstractmethod
    def save_events(self, events: List[TimelineEventEntity]) -> None: pass

    @abstractmethod
    def get_canonical_timeline(self, driver_id: str, days_back: int) -> List[TimelineEventEntity]: pass

class PostgresMockTimelineRepository(TimelineRepository):
    """Mock relacyjnej bazy danych działający w pamięci operacyjnej."""
    def __init__(self):
        self._db: Dict[str, List[TimelineEventEntity]] = {}

    def save_events(self, events: List[TimelineEventEntity]) -> None:
        for ev in events:
            if ev.driver_id not in self._db: self._db[ev.driver_id] = []
            self._db[ev.driver_id].append(ev)

    def get_canonical_timeline(self, driver_id: str, days_back: int) -> List[TimelineEventEntity]:
        if driver_id not in self._db: return []
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
        events = [e for e in self._db[driver_id] if e.start_time_utc >= cutoff]
        events.sort(key=lambda x: x.start_time_utc)
        return events

# =========================================================
# 6. SERVICE LAYER: OCR & TIMELINE RECONSTRUCTION
# =========================================================

class OCRExtractionResultMock(BaseModel):
    document_date: str
    events: List[OCRTimelineEvent]
    overall_confidence: float

class OCRService:
    def extract(self, image_bytes) -> Tuple[str, List[OCRTimelineEvent], float]:
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        sys_prompt = "Analyze tachograph printout. Strict HH:MM format."
        res = client.beta.chat.completions.parse(
            model=OPENAI_MODEL_VISION,
            messages=[{"role": "system", "content": sys_prompt},
                      {"role": "user", "content": [{"type": "text", "text": "Extract timeline."}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}] }],
            response_format=OCRExtractionResultMock, temperature=0
        )
        parsed = res.choices[0].message.parsed
        return parsed.document_date, parsed.events, parsed.overall_confidence

class TimelineService:
    def __init__(self, repo: TimelineRepository):
        self.repo = repo

    def process_and_save(self, audit_id: str, driver_id: str, doc_date: str, raw_events: List[OCRTimelineEvent]) -> List[TimelineEventEntity]:
        clean_date = datetime.strptime(re.search(r"(\d{2}[./-]\d{2}[./-]\d{4})", doc_date).group(1).replace("-", ".").replace("/", "."), "%d.%m.%Y").replace(tzinfo=timezone.utc)
        
        parsed = []
        prev_start = None
        for r in raw_events:
            sh, sm = map(int, r.start_time_raw.split(":"))
            eh, em = map(int, r.end_time_raw.split(":"))
            s_dt = clean_date.replace(hour=sh, minute=sm)
            e_dt = clean_date.replace(hour=eh, minute=em)
            
            if prev_start and s_dt < prev_start: clean_date += timedelta(days=1); s_dt += timedelta(days=1); e_dt += timedelta(days=1)
            if e_dt < s_dt: e_dt += timedelta(days=1)
            
            parsed.append({"s": s_dt, "e": e_dt, "act": r.activity, "conf": r.confidence})
            prev_start = s_dt

        parsed.sort(key=lambda x: x["s"])
        
        healed, parent_hash = [], "0"*64
        for p in parsed:
            if healed and p["s"] < healed[-1]["e"]:
                p["s"] = healed[-1]["e"]
                p["conf"] *= ConfidencePolicy.TRUNCATION_DECAY
            if healed and p["s"] > healed[-1]["e"]:
                dur = int((p["s"] - healed[-1]["e"]).total_seconds() / 60)
                healed.append({"s": healed[-1]["e"], "e": p["s"], "act": EventType.UNKNOWN, "conf": ConfidencePolicy.SYNTHETIC_GAP})
            healed.append(p)

        entities = []
        for h in healed:
            dur = int((h["e"] - h["s"]).total_seconds() / 60)
            if dur <= 0: continue
            i_hash = hashlib.sha256(f"{parent_hash}{h['s']}{h['e']}{h['act']}{dur}".encode()).hexdigest()
            entities.append(TimelineEventEntity(
                id=str(uuid.uuid4()), audit_id=audit_id, driver_id=driver_id,
                integrity_hash=i_hash, parent_hash=parent_hash, start_time_utc=h["s"], end_time_utc=h["e"],
                activity=h["act"], duration_minutes=dur, confidence=h["conf"], created_at=datetime.now(timezone.utc)
            ))
            parent_hash = i_hash

        self.repo.save_events(entities)
        return entities

# =========================================================
# 7. SERVICE LAYER: RULE ENGINE & STATE MACHINE
# =========================================================

class DriverStateContext(BaseModel):
    continuous_driving_minutes: int = 0
    daily_driving_minutes: int = 0
    current_break_sequence: List[int] = Field(default_factory=list)
    current_driving_events: List[TimelineEventEntity] = Field(default_factory=list)

class RuleService:
    def evaluate(self, audit_id: str, timeline: List[TimelineEventEntity], pack: JurisdictionPack) -> List[ViolationRecord]:
        violations = []
        ctx = DriverStateContext()
        
        for ev in timeline:
            if ev.activity == EventType.DRIVING:
                ctx.continuous_driving_minutes += ev.duration_minutes
                ctx.daily_driving_minutes += ev.duration_minutes
                ctx.current_break_sequence.clear()
                ctx.current_driving_events.append(ev)
            elif ev.activity == EventType.BREAK:
                ctx.current_break_sequence.append(ev.duration_minutes)
                if ev.duration_minutes >= 45 or (ev.duration_minutes >= 30 and any(b >= 15 for b in ctx.current_break_sequence[:-1])):
                    ctx.continuous_driving_minutes = 0
                    ctx.current_break_sequence.clear()
                    ctx.current_driving_events.clear()
            elif ev.activity == EventType.UNKNOWN and pack.unknown_policy == UnknownPolicy.STRICT:
                ctx.continuous_driving_minutes += ev.duration_minutes
            else:
                ctx.current_break_sequence.clear()

            # Art 7 Rule Evaluation
            if ctx.continuous_driving_minutes > (270 + pack.tolerance_minutes):
                exc = ctx.continuous_driving_minutes - 270
                ev_ids = [e.id for e in ctx.current_driving_events]
                ev_conf = min([e.confidence for e in ctx.current_driving_events] or [1.0])
                
                violations.append(ViolationRecord(
                    id=str(uuid.uuid4()), audit_id=audit_id, rule_id="ART7", article="Art. 7",
                    description=f"Przekroczenie ciągłej jazdy o {exc} min.",
                    explanation=f"Zgromadzono {ctx.continuous_driving_minutes} min bez 45 min pauzy (lub 15+30).",
                    severity=Severity.HIGH if exc > 60 else Severity.MEDIUM,
                    estimated_fine_eur=pack.calculate_fine("ART7_CONTINUOUS_DRIVING", exc),
                    confidence=round(0.95 * ev_conf, 2), evidence_event_ids=ev_ids
                ))
                ctx.continuous_driving_minutes = 0

        return violations

# =========================================================
# 8. SERVICE LAYER: EVIDENCE-BASED DEFENSE ENGINE
# =========================================================

class DefenseService:
    def assess(self, violations: List[ViolationRecord], evidence: ExternalEvidence) -> List[ViolationRecord]:
        for v in violations:
            score = 0.10
            strategy = []
            
            if evidence.traffic_jam_detected:
                score += 0.40
                strategy.append("Telematyka potwierdza zator drogowy.")
            if evidence.accident_on_route:
                score += 0.50
                strategy.append("Udokumentowany wypadek na trasie.")
            if evidence.parking_unavailable:
                score += 0.30
                strategy.append("Brak miejsc parkingowych.")
            if evidence.border_delay:
                score += 0.35
                strategy.append("Opóźnienie na przejściu granicznym.")

            v.defense_score = min(1.0, score)
            
            if v.defense_score > 0.70:
                v.defense_strategy = " | ".join(strategy) + " -> Bardzo mocne dowody z Art. 12."
            elif v.defense_score > 0.30:
                v.defense_strategy = " | ".join(strategy) + " -> Umiarkowane szanse."
            else:
                v.defense_strategy = "Słabe dowody. Znikoma szansa na zastosowanie Art. 12."
                
        return violations

# =========================================================
# 9. ORCHESTRATION LAYER: AUDIT SERVICE
# =========================================================

class AuditService:
    def __init__(self):
        self.repo = PostgresMockTimelineRepository()
        self.ocr_svc = OCRService()
        self.timeline_svc = TimelineService(self.repo)
        self.rule_svc = RuleService()
        self.defense_svc = DefenseService()

    def run_audit(self, driver_id: str, image_bytes, external_evidence: ExternalEvidence, pack: JurisdictionPack = POLAND_PACK_2025):
        audit_id = str(uuid.uuid4())
        
        doc_date, raw_events, _ = self.ocr_svc.extract(image_bytes)
        if not raw_events: return {"status": "NO_EVENTS"}

        self.timeline_svc.process_and_save(audit_id, driver_id, doc_date, raw_events)
        canonical_timeline = self.repo.get_canonical_timeline(driver_id, days_back=28)
        violations = self.rule_svc.evaluate(audit_id, canonical_timeline, pack)
        defended_violations = self.defense_svc.assess(violations, external_evidence)

        total_fine = sum(v.estimated_fine_eur for v in defended_violations)
        return AuditRecord(
            id=audit_id, driver_id=driver_id, created_at=datetime.now(timezone.utc),
            status="NON_COMPLIANT" if defended_violations else "COMPLIANT",
            violations=defended_violations, total_fine_eur=total_fine, timeline_confidence=0.9
        ).model_dump()

# =========================================================
# BACKWARD COMPATIBILITY ADAPTER (FASADA DLA APP.PY)
# =========================================================
class AuditPipeline:
    """
    Adapter zachowujący pełną wsteczną kompatybilność ze Streamlit (app.py).
    Kapsułkuje nowy AuditService, żeby front-end nie zauważył zmiany architektury.
    """
    def __init__(self):
        self.service = AuditService()

    def run(self, image_bytes, profile=POLAND_PACK_2025):
        # Domyślny, bezpieczny dowód telematyczny chroniący przed awarią interfejsu
        fallback_evidence = ExternalEvidence(
            traffic_jam_detected=False,
            accident_on_route=False,
            weather_alert_active=False,
            parking_unavailable=False,
            border_delay=False,
            ferry_or_train_crossing=False
        )
        
        # Przekierowanie wywołania ze starego interfejsu do nowoczesnego serwisu
        return self.service.run_audit(
            driver_id="STREAMLIT_DRIVER", 
            image_bytes=image_bytes, 
            external_evidence=fallback_evidence, 
            pack=profile
        )
