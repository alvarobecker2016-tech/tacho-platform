# =========================================================
# POCKET DGSA & TACHO
# ENTERPRISE COMPLIANCE AI ENGINE v20
# API-STABLE CORE (SOA + STRICT DTO CONTRACT FOR STREAMLIT)
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
# 2. DOMAIN LAYER: EXTERNAL EVIDENCE & JURISDICTIONS
# =========================================================

class ExternalEvidence(BaseModel):
    traffic_jam_detected: bool = False
    accident_on_route: bool = False
    weather_alert_active: bool = False
    parking_unavailable: bool = False
    border_delay: bool = False
    ferry_or_train_crossing: bool = False

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
# 3. DTO LAYER: STRICT FRONTEND CONTRACT (APP.PY COMPATIBILITY)
# =========================================================
# Te klasy musza zostać w niezmienionej formie, by uniknąć KeyError w UI

class AuditFlag(BaseModel):
    code: str
    severity: Severity
    description: str

class ReconstructionStats(BaseModel):
    events_corrected: int = 0
    events_dropped: int = 0
    gaps_inserted: int = 0
    duplicates_removed: int = 0

class TimelineEvent(BaseModel):
    event_id: str
    integrity_hash: str
    parent_hash: str
    start_time_utc: datetime
    end_time_utc: datetime
    original_start_time_utc: Optional[datetime] = None
    original_end_time_utc: Optional[datetime] = None
    activity: EventType
    duration_minutes: int
    source: str
    confidence: float
    is_corrected: bool = False
    correction_reason: Optional[str] = None
    created_at: datetime

class Violation(BaseModel):
    violation_id: str
    rule_id: str
    article: str
    regulation: str
    description: str
    explanation: str
    severity: Severity
    estimated_fine_eur: Optional[int]
    confidence: float
    defense_possible: bool
    defense_score: float = 0.0
    defense_strategy: Optional[str] = None
    evidence_event_ids: List[str]
    triggered_at: datetime

class AuditTrace(BaseModel):
    audit_id: str
    started_at: datetime
    finished_at: Optional[datetime]
    ocr_latency_ms: Optional[float]
    rule_engine_latency_ms: Optional[float]
    legal_engine_latency_ms: Optional[float]
    total_execution_ms: Optional[float]
    model_vision: str
    model_fast: str
    rules_executed: int
    violations_detected: int
    timeline_confidence_avg: float = 0.0
    timeline_confidence_min: float = 0.0
    timeline_confidence_weighted: float = 0.0
    reconstruction_stats: ReconstructionStats = Field(default_factory=ReconstructionStats)
    flags: List[AuditFlag] = Field(default_factory=list)

class AuditReport(BaseModel):
    audit_id: str
    created_at: datetime
    summary: str
    violations: List[Violation]
    total_risk_score: float
    compliance_status: str
    confidence_score: float
    trace: AuditTrace

# =========================================================
# 4. SERVICE LAYER: REPOSITORY & OCR
# =========================================================

class TimelineRepository(ABC):
    @abstractmethod
    def save_events(self, driver_id: str, events: List[TimelineEvent]) -> None: pass

    @abstractmethod
    def get_canonical_timeline(self, driver_id: str, days_back: int) -> List[TimelineEvent]: pass

class PostgresMockTimelineRepository(TimelineRepository):
    def __init__(self):
        self._db: Dict[str, List[TimelineEvent]] = {}

    def save_events(self, driver_id: str, events: List[TimelineEvent]) -> None:
        if driver_id not in self._db: self._db[driver_id] = []
        self._db[driver_id].extend(events)

    def get_canonical_timeline(self, driver_id: str, days_back: int) -> List[TimelineEvent]:
        if driver_id not in self._db: return []
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
        events = [e for e in self._db[driver_id] if e.start_time_utc >= cutoff]
        events.sort(key=lambda x: x.start_time_utc)
        return events

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

    @field_validator("confidence", mode="before")
    @classmethod
    def normalize_conf(cls, value):
        try:
            v = float(str(value).replace("%", "").strip())
            return v / 100.0 if v > 1.0 else v
        except: return 0.0

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

# =========================================================
# 5. SERVICE LAYER: TIMELINE RECONSTRUCTION
# =========================================================

class TimelineService:
    def __init__(self, repo: TimelineRepository):
        self.repo = repo

    def process_and_save(self, audit_id: str, driver_id: str, doc_date: str, raw_events: List[OCRTimelineEvent]) -> Tuple[List[TimelineEvent], List[AuditFlag], ReconstructionStats]:
        clean_date = datetime.strptime(re.search(r"(\d{2}[./-]\d{2}[./-]\d{4})", doc_date).group(1).replace("-", ".").replace("/", "."), "%d.%m.%Y").replace(tzinfo=timezone.utc)
        
        parsed_events, flags_dict, stats = [], {}, ReconstructionStats()
        def add_flag(code: str, severity: Severity, description: str):
            if code not in flags_dict: flags_dict[code] = AuditFlag(code=code, severity=severity, description=description)

        prev_start = None
        for r in raw_events:
            try:
                sh, sm = map(int, r.start_time_raw.split(":"))
                eh, em = map(int, r.end_time_raw.split(":"))
                if sh > 23 or sm > 59 or eh > 23 or em > 59:
                    stats.events_dropped += 1
                    continue
                s_dt = clean_date.replace(hour=sh, minute=sm)
                e_dt = clean_date.replace(hour=eh, minute=em)
                
                if prev_start and s_dt < prev_start: clean_date += timedelta(days=1); s_dt += timedelta(days=1); e_dt += timedelta(days=1)
                if e_dt < s_dt: e_dt += timedelta(days=1)
                
                parsed_events.append({"s": s_dt, "e": e_dt, "act": r.activity, "conf": r.confidence, "is_corr": False, "reason": None, "orig_s": None, "orig_e": None})
                prev_start = s_dt
            except:
                stats.events_dropped += 1
                continue

        parsed_events.sort(key=lambda x: x["s"])
        
        healed, parent_hash = [], "0"*64
        for p in parsed_events:
            if not healed:
                healed.append(p)
                continue
            prev = healed[-1]

            if p["s"] == prev["s"] and p["e"] == prev["e"] and p["act"] == prev["act"]:
                add_flag("DEDUPLICATION_APPLIED", Severity.LOW, "Usunięto duplikaty OCR.")
                stats.duplicates_removed += 1
                continue

            if p["s"] < prev["e"]:
                add_flag("OVERLAP_CORRECTED", Severity.MEDIUM, "Obcięto nakładające się zdarzenia.")
                p["orig_s"], p["orig_e"] = p["s"], p["e"]
                p["s"] = prev["e"]
                p["is_corr"], p["reason"] = True, "OVERLAP_TRUNCATION"
                p["conf"] = max(ConfidencePolicy.MIN_CONFIDENCE, p["conf"] * ConfidencePolicy.TRUNCATION_DECAY)
                stats.events_corrected += 1
                if p["s"] >= p["e"]:
                    stats.events_dropped += 1
                    continue

            if p["s"] > prev["e"]:
                if int((p["s"] - prev["e"]).total_seconds() / 60) > 0:
                    add_flag("GAP_DETECTED", Severity.HIGH, "Wstrzyknięto UNKNOWN w lukę.")
                    healed.append({"s": prev["e"], "e": p["s"], "act": EventType.UNKNOWN, "conf": ConfidencePolicy.SYNTHETIC_GAP, "is_corr": True, "reason": "GAP_INSERTION", "orig_s": None, "orig_e": None})
                    stats.gaps_inserted += 1

            healed.append(p)

        entities = []
        for h in healed:
            dur = int((h["e"] - h["s"]).total_seconds() / 60)
            if dur <= 0: continue
            i_hash = hashlib.sha256(f"{parent_hash}{h['s']}{h['e']}{h['act']}{dur}".encode()).hexdigest()
            src = "HEALER_CORRECTION" if h["is_corr"] else ("HEALER_ENGINE" if h["act"] == EventType.UNKNOWN else "OCR_ENGINE")
            
            entities.append(TimelineEvent(
                event_id=str(uuid.uuid4()), integrity_hash=i_hash, parent_hash=parent_hash,
                start_time_utc=h["s"], end_time_utc=h["e"], original_start_time_utc=h["orig_s"],
                original_end_time_utc=h["orig_e"], activity=h["act"], duration_minutes=dur,
                source=src, confidence=h["conf"], is_corrected=h["is_corr"], correction_reason=h["reason"],
                created_at=datetime.now(timezone.utc)
            ))
            parent_hash = i_hash

        self.repo.save_events(driver_id, entities)
        return entities, sorted(list(flags_dict.values()), key=lambda x: x.code), stats

# =========================================================
# 6. SERVICE LAYER: RULE ENGINE & DEFENSE ENGINE
# =========================================================

class DriverStateContext(BaseModel):
    continuous_driving_minutes: int = 0
    daily_driving_minutes: int = 0
    current_break_sequence: List[int] = Field(default_factory=list)
    current_driving_events: List[TimelineEvent] = Field(default_factory=list)
    triggered_rules: List[str] = Field(default_factory=list)

class RuleService:
    def evaluate(self, audit_id: str, timeline: List[TimelineEvent], pack: JurisdictionPack) -> List[Violation]:
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

            # Art 7. Rule Evaluation
            rule_key = f"ART7_{ev.event_id}"
            if ctx.continuous_driving_minutes > (270 + pack.tolerance_minutes) and rule_key not in ctx.triggered_rules:
                exc = ctx.continuous_driving_minutes - 270
                ev_ids = [e.event_id for e in ctx.current_driving_events]
                ev_conf = min([e.confidence for e in ctx.current_driving_events] or [1.0])
                
                violations.append(Violation(
                    violation_id=str(uuid.uuid4()), rule_id="ART7", article="Art. 7", regulation="561/2006",
                    description=f"Przekroczenie ciągłej jazdy o {exc} min.",
                    explanation=f"Zgromadzono {ctx.continuous_driving_minutes} min bez 45 min pauzy (lub 15+30).",
                    severity=Severity.HIGH if exc > 60 else Severity.MEDIUM,
                    estimated_fine_eur=pack.calculate_fine("ART7_CONTINUOUS_DRIVING", exc),
                    confidence=round(0.95 * ev_conf, 2), defense_possible=True,
                    evidence_event_ids=ev_ids, triggered_at=datetime.now(timezone.utc)
                ))
                ctx.triggered_rules.append(rule_key)
                ctx.continuous_driving_minutes = 0 

        return violations

class DefenseService:
    def assess(self, violations: List[Violation], evidence: ExternalEvidence) -> List[Violation]:
        for v in violations:
            if not v.defense_possible: continue
            score = 0.10
            strategy = []
            
            if evidence.traffic_jam_detected: score += 0.40; strategy.append("Zator drogowy")
            if evidence.accident_on_route: score += 0.50; strategy.append("Wypadek")
            if evidence.parking_unavailable: score += 0.30; strategy.append("Brak parkingu")
            if evidence.border_delay: score += 0.35; strategy.append("Opóźnienie na granicy")

            v.defense_score = min(1.0, score)
            
            if v.defense_score > 0.70: v.defense_strategy = " | ".join(strategy) + " -> Bardzo mocne dowody (Art. 12)."
            elif v.defense_score > 0.30: v.defense_strategy = " | ".join(strategy) + " -> Umiarkowane szanse."
            else: v.defense_strategy = "Słabe dowody. Znikoma szansa."
                
        return violations

# =========================================================
# 7. SERVICE LAYER: REPORT GENERATION
# =========================================================

class ReportService:
    def generate(self, audit_id: str, violations: List[Violation], trace: AuditTrace, ocr_conf: float) -> AuditReport:
        if not violations:
            return AuditReport(
                audit_id=audit_id, created_at=datetime.now(timezone.utc),
                summary="Brak naruszeń. Analiza osi czasu zakończona powodzeniem.",
                violations=[], total_risk_score=0.1, compliance_status="COMPLIANT",
                confidence_score=ocr_conf, trace=trace
            )
            
        summary = "\n".join([f"- {v.article} ({v.regulation}) | {v.description}" for v in violations])
        return AuditReport(
            audit_id=audit_id, created_at=datetime.now(timezone.utc), summary=summary,
            violations=violations, total_risk_score=min(len(violations) * 0.2, 1.0),
            compliance_status="NON_COMPLIANT", confidence_score=ocr_conf, trace=trace
        )

# =========================================================
# 8. ORCHESTRATION LAYER: AUDIT SERVICE
# =========================================================

class AuditService:
    def __init__(self):
        self.repo = PostgresMockTimelineRepository()
        self.ocr_svc = OCRService()
        self.timeline_svc = TimelineService(self.repo)
        self.rule_svc = RuleService()
        self.defense_svc = DefenseService()
        self.report_svc = ReportService()

    def run_audit(self, driver_id: str, image_bytes, evidence: ExternalEvidence, pack: JurisdictionPack) -> AuditReport:
        audit_id = str(uuid.uuid4())
        start_time = time.time()
        
        trace = AuditTrace(
            audit_id=audit_id, started_at=datetime.now(timezone.utc), finished_at=None,
            ocr_latency_ms=0.0, rule_engine_latency_ms=0.0, legal_engine_latency_ms=0.0, total_execution_ms=0.0,
            model_vision=OPENAI_MODEL_VISION, model_fast=OPENAI_MODEL_FAST, rules_executed=1, violations_detected=0, flags=[]
        )

        # 1. OCR Extract
        ocr_start = time.time()
        doc_date, raw_events, ocr_conf = self.ocr_svc.extract(image_bytes)
        trace.ocr_latency_ms = (time.time() - ocr_start) * 1000

        if not raw_events: 
            return self._early_exit(audit_id, trace, "NO_EVENTS_FOUND", "OCR nie wykrył zdarzeń.", ocr_conf)
        if ocr_conf < CONFIDENCE_THRESHOLD:
            return self._early_exit(audit_id, trace, "UNCERTAIN", "Jakość dokumentu jest zbyt niska.", ocr_conf)

        # 2. Reconstruct & Save
        try:
            _, flags, stats = self.timeline_svc.process_and_save(audit_id, driver_id, doc_date, raw_events)
            trace.flags.extend(flags)
            trace.reconstruction_stats = stats
        except Exception as e:
            return self._early_exit(audit_id, trace, "RECONSTRUCTION_ERROR", str(e), ocr_conf)

        # 3. Canonical Timeline
        canonical = self.repo.get_canonical_timeline(driver_id, days_back=28)
        if not canonical:
            return self._early_exit(audit_id, trace, "TIMELINE_EMPTY", "Pusta oś czasu po weryfikacji.", ocr_conf)

        # Confidence Aggregation
        confs = [e.confidence for e in canonical]
        trace.timeline_confidence_avg = round(sum(confs) / len(confs), 2)
        trace.timeline_confidence_min = round(min(confs), 2)
        
        weights = {EventType.DRIVING: 1.5, EventType.OTHER_WORK: 1.2, EventType.UNKNOWN: 0.5}
        w_sum = sum(e.confidence * (weights.get(e.activity, 1.0) * max(e.duration_minutes, 1)) for e in canonical)
        t_weight = sum((weights.get(e.activity, 1.0) * max(e.duration_minutes, 1)) for e in canonical)
        trace.timeline_confidence_weighted = round(w_sum / t_weight, 2) if t_weight > 0 else 0.0

        # 4. Rules
        rules_start = time.time()
        violations = self.rule_svc.evaluate(audit_id, canonical, pack)
        trace.rule_engine_latency_ms = (time.time() - rules_start) * 1000
        trace.violations_detected = len(violations)

        # 5. Defense
        defended_violations = self.defense_svc.assess(violations, evidence)

        # 6. Reporting
        legal_start = time.time()
        trace.total_execution_ms = (time.time() - start_time) * 1000
        trace.finished_at = datetime.now(timezone.utc)
        trace.legal_engine_latency_ms = (time.time() - legal_start) * 1000

        return self.report_svc.generate(audit_id, defended_violations, trace, ocr_conf)
        
    def _early_exit(self, audit_id, trace, status, message, conf) -> dict:
        # Fallback dictionary for Streamlit compatibility on errors
        return {"status": status, "message": message}

# =========================================================
# BACKWARD COMPATIBILITY ADAPTER (FASADA DLA APP.PY)
# =========================================================

class AuditPipeline:
    """
    Adapter (Fasada).
    Zapewnia pełną kompatybilność ze starym formatem wejścia/wyjścia (Streamlit app.py),
    podczas gdy w tle pracuje nowa, zorientowana na serwisy architektura (AuditService).
    """
    def __init__(self):
        self.service = AuditService()

    def run(self, image_bytes, profile=POLAND_PACK_2025):
        # Domyślny, pusty dowód telematyczny chroniący przed awarią interfejsu
        fallback_evidence = ExternalEvidence(
            traffic_jam_detected=False, accident_on_route=False, weather_alert_active=False,
            parking_unavailable=False, border_delay=False, ferry_or_train_crossing=False
        )
        
        result = self.service.run_audit(
            driver_id="STREAMLIT_DRIVER", 
            image_bytes=image_bytes, 
            evidence=fallback_evidence, 
            pack=profile
        )
        
        # Ochrona dla errorów przedwczesnych zdefiniowanych w early_exit
        if isinstance(result, dict) and "status" in result and result["status"] != "NON_COMPLIANT" and result["status"] != "COMPLIANT":
            return result
            
        # Zrzut modelu DTO gotowego do przetworzenia w Streamlit
        return result.model_dump()
