# =========================================================
# models/domain.py - STRUKTURY DANYCH V7 (PYDANTIC)
# =========================================================

from enum import Enum
from datetime import datetime
from typing import List, Optional, Set
from pydantic import BaseModel, Field

# --- ENUMY ---
class EventType(str, Enum):
    DRIVING = "DRIVING"
    BREAK = "BREAK"
    REST = "REST"
    OTHER_WORK = "OTHER_WORK"
    AVAILABILITY = "AVAILABILITY"

class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

# --- STRUKTURY OCR ---
class OCRHeader(BaseModel):
    document_date: str
    timezone_hint: Optional[str] = "UTC"

class OCRTimelineEvent(BaseModel):
    start_time_raw: str
    end_time_raw: str
    activity: EventType
    confidence: float = Field(ge=0.0, le=1.0)

class OCRExtractionResult(BaseModel):
    driver_name: str
    card_number: str
    header: OCRHeader
    events: List[OCRTimelineEvent]
    overall_confidence: float

# --- METADANE REGUŁ ---
class RuleMetadata(BaseModel):
    rule_id: str
    article: str
    regulation: str
    version: str
    country_scope: List[str]
    priority: int
    deterministic: bool = True

# --- PROFIL ORGANU KONTROLNEGO ---
class EnforcementProfile(BaseModel):
    country_code: str
    authority_name: str
    tolerance_minutes: int
    fine_multiplier: float
    aggressive_mode: bool = False

# --- REKONSTRUOWANY EVENT ---
class TimelineEvent(BaseModel):
    event_id: str
    integrity_hash: str
    start_time_utc: datetime
    end_time_utc: datetime
    activity: EventType
    duration_minutes: int
    source: str
    confidence: float
    created_at: datetime

# --- MASZYNA STANÓW (CONTEXT KIEROWCY) ---
class DriverStateContext(BaseModel):
    continuous_driving_minutes: int = 0
    daily_driving_minutes: int = 0
    weekly_driving_minutes: int = 0
    current_break_sequence: List[int] = []
    current_chain_event_ids: List[str] = []
    current_daily_rest_minutes: int = 0
    reduced_daily_rests_used: int = 0
    split_break_active: bool = False
    triggered_rules: Set[str] = set()
    last_event_time: Optional[datetime] = None

# --- WYNIKI AUDYTU (NARUSZENIA I RAPORTY) ---
class Violation(BaseModel):
    violation_id: str
    rule_id: str
    article: str
    regulation: str
    description: str
    severity: Severity
    estimated_fine_eur: Optional[int]
    confidence: float
    defense_possible: bool
    defense_strategy: Optional[str]
    evidence_event_ids: List[str]
    triggered_at: datetime

class RuleEvaluationResult(BaseModel):
    violations: List[Violation] = []
    warnings: List[str] = []
    execution_time_ms: float = 0.0
    matched_conditions: List[str] = []

class AuditTrace(BaseModel):
    audit_id: str
    started_at: datetime
    finished_at: Optional[datetime]
    ocr_latency_ms: Optional[float]
    reconstruction_latency_ms: Optional[float]
    rule_engine_latency_ms: Optional[float]
    legal_engine_latency_ms: Optional[float]
    total_execution_ms: Optional[float]
    model_vision: str
    model_fast: str
    rules_executed: int
    violations_detected: int

class AuditReport(BaseModel):
    audit_id: str
    created_at: datetime
    summary: str
    violations: List[Violation]
    total_risk_score: float
    compliance_status: str
    confidence_score: float
    trace: AuditTrace