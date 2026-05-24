import hmac
import hashlib
import os
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import List, Optional, Tuple
from zoneinfo import ZoneInfo

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn

# ==============================================================================
# 0. CENTRALIZED IMMUTABLE KERNEL VERSIONING (Forensic Integrity)
# ==============================================================================
KERNEL_VERSION = "1.5.0_defensive"
KERNEL_BUILD_ID = os.getenv("KERNEL_BUILD_ID", "sha256:d8f3a1e2b9c4f5a6b7c8d9e0f1a2b3c4")
LEGAL_POLICY_VERSION = os.getenv("LEGAL_POLICY_VERSION", "POLICY_EU_2026_01")
APP_SECRET_KEY = os.getenv("APP_SECRET_KEY", "prod-immutable-fallback-hmac-key-2026").encode()

# ==============================================================================
# 1. ONTOLOGY & APPLICABILITY CONTEXT
# ==============================================================================
class TransportType(str, Enum):
    FREIGHT = "FREIGHT"
    PASSENGER_REGULAR = "PASSENGER_REGULAR"
    PASSENGER_OCCASIONAL = "PASSENGER_OCCASIONAL"

class RegulatoryDomain(str, Enum):
    EU_561_2006 = "EU_561_2006"
    AETR = "AETR"

class CrewMode(str, Enum):
    SINGLE = "SINGLE"
    MULTI_MANNING = "MULTI_MANNING"

class ApplicabilityContext(BaseModel):
    transport_type: TransportType = TransportType.FREIGHT
    regulatory_domain: RegulatoryDomain = RegulatoryDomain.EU_561_2006
    crew_mode: CrewMode = CrewMode.SINGLE
    vehicle_mma_kg: int = Field(default=40000, ge=0)

# ==============================================================================
# 2. RAW EVENTS & HARDENED CONSTRAINTS
# ==============================================================================
class ActivityType(str, Enum):
    DRIVING = "DRIVING"
    REST = "REST"
    WORK = "WORK"
    AVAIL = "AVAIL"
    UNKNOWN = "UNKNOWN"

class EventSourceType(str, Enum):
    OCR = "OCR"
    USER_CORRECTED = "USER_CORRECTED"
    SYNTHETIC_IMPUTATION = "SYNTHETIC_IMPUTATION"

class GapSeverity(str, Enum):
    NOT_A_GAP = "NOT_A_GAP"
    MICRO_GAP = "MICRO_GAP"
    SOFT_GAP = "SOFT_GAP"
    HARD_GAP = "HARD_GAP"
    STRUCTURAL_BREAK = "STRUCTURAL_BREAK"

class TimeContext(BaseModel):
    utc_timestamp: datetime
    timezone_name: str = "Europe/Warsaw"

class ConfidenceMetrics(BaseModel):
    ocr_fidelity: float = Field(ge=0.0, le=1.0)          
    symbol_classification: float = Field(ge=0.0, le=1.0) 
    spatial_consistency: float = Field(ge=0.0, le=1.0)   
    
    @property
    def aggregated_score(self) -> float:
        if self.spatial_consistency < 0.25:
            return min(0.15, self.ocr_fidelity)
        return (0.25 * self.ocr_fidelity) + (0.40 * self.symbol_classification) + (0.35 * self.spatial_consistency)

class CanonicalEvent(BaseModel):
    event_id: str
    activity: ActivityType
    duration_minutes: int = Field(gt=0) 
    time_context: TimeContext
    confidence: ConfidenceMetrics
    source_type: EventSourceType = EventSourceType.OCR
    gap_severity: GapSeverity = GapSeverity.NOT_A_GAP

# ==============================================================================
# 3. STRICT TEMPORAL GATEWAY (Fail-Closed)
# ==============================================================================
class StrictTemporalValidator:
    @staticmethod
    def enforce_physics(events: List[CanonicalEvent]) -> List[CanonicalEvent]:
        if not events:
            raise HTTPException(status_code=400, detail="Brak danych wejściowych.")
            
        sorted_events = sorted(events, key=lambda e: e.time_context.utc_timestamp)
        patched_timeline = []
        
        for i, curr_event in enumerate(sorted_events):
            if i > 0:
                prev_event = sorted_events[i-1]
                prev_end = prev_event.time_context.utc_timestamp + timedelta(minutes=prev_event.duration_minutes)
                delta_minutes = (curr_event.time_context.utc_timestamp - prev_end).total_seconds() / 60.0
                
                if delta_minutes <= -1:
                    raise HTTPException(
                        status_code=400, 
                        detail={
                            "error": f"Konflikt spójności osi czasu: Nakładanie o {abs(int(delta_minutes))} min.",
                            "legal_basis": "Rozporządzenie (UE) nr 165/2014, Artykuł 34",
                            "explanation": "Zgodnie z przepisami o tachografach, fizycznie niemożliwe jest rejestrowanie dwóch różnych aktywności w tym samym czasie. System odrzuca uszkodzony graf dowodowy."
                        }
                    )
                
                elif delta_minutes >= 1:
                    sev = GapSeverity.MICRO_GAP
                    if delta_minutes >= 45: sev = GapSeverity.STRUCTURAL_BREAK
                    elif delta_minutes >= 15: sev = GapSeverity.HARD_GAP
                    elif delta_minutes >= 5: sev = GapSeverity.SOFT_GAP
                    
                    patched_timeline.append(CanonicalEvent(
                        event_id=f"gap_{prev_end.timestamp()}",
                        activity=ActivityType.UNKNOWN,
                        duration_minutes=int(delta_minutes),
                        time_context=TimeContext(utc_timestamp=prev_end, timezone_name=curr_event.time_context.timezone_name),
                        confidence=ConfidenceMetrics(ocr_fidelity=0.0, symbol_classification=0.0, spatial_consistency=1.0),
                        source_type=EventSourceType.SYNTHETIC_IMPUTATION,
                        gap_severity=sev
                    ))
                    
            patched_timeline.append(curr_event)
            
        return patched_timeline

# ==============================================================================
# 4. INTERNAL LEGAL LAYER (Strict Law Assessment)
# ==============================================================================
class ContinuityState(str, Enum):
    MAINTAINED = "MAINTAINED"
    BROKEN_UNCERTAIN = "BROKEN_UNCERTAIN"
    BROKEN_VIOLATION = "BROKEN_VIOLATION"

class LegalSeverity(str, Enum):
    NONE = "NONE"
    MINOR = "MINOR"
    SERIOUS = "SERIOUS_INFRINGEMENT"
    VERY_SERIOUS = "VERY_SERIOUS_INFRINGEMENT"

class BreakState(BaseModel):
    first_split_duration: int = 0
    def register_break_and_check_reset(self, duration: int, context: ApplicabilityContext) -> bool:
        if duration >= 45: return True
        if duration >= 30 and self.first_split_duration >= 15: return True
        if duration >= 15 and self.first_split_duration < 15: 
            self.first_split_duration = duration
        return False
    def reset(self): 
        self.first_split_duration = 0

class DrivingState(BaseModel):
    continuous_driving: int = 0
    break_accumulator: BreakState = Field(default_factory=BreakState)
    trajectory_confidence: float = 1.0 
    last_state_reset_reason: str = "NEW_SHIFT_INITIALIZED" 
    
    def reset_clean(self, reason: str):
        self.continuous_driving = 0
        self.break_accumulator.reset()
        self.trajectory_confidence = 1.0
        self.last_state_reset_reason = reason

class LegalAssessment(BaseModel):
    rule_reference: str = "561/2006 Art.7"
    continuity_state: ContinuityState
    severity: LegalSeverity
    accumulated_driving_minutes: int
    trajectory_confidence: float
    trigger_event_id: Optional[str] = None
    state_reset_reason: str

class Regulation561_Art7_Engine:
    def evaluate(self, events: List[CanonicalEvent], context: ApplicabilityContext) -> List[LegalAssessment]:
        assessments = []
        state = DrivingState()
        
        for event in events:
            state.trajectory_confidence = min(state.trajectory_confidence, event.confidence.aggregated_score)
            
            if event.activity == ActivityType.DRIVING:
                state.continuous_driving += event.duration_minutes
                if state.continuous_driving > 270:
                    sev = LegalSeverity.VERY_SERIOUS if state.continuous_driving > 300 else LegalSeverity.SERIOUS
                    assessments.append(LegalAssessment(
                        continuity_state=ContinuityState.BROKEN_VIOLATION, severity=sev,
                        accumulated_driving_minutes=state.continuous_driving, trajectory_confidence=state.trajectory_confidence,
                        trigger_event_id=event.event_id, state_reset_reason=state.last_state_reset_reason
                    ))
                    
            elif event.activity == ActivityType.REST:
                if state.break_accumulator.register_break_and_check_reset(event.duration_minutes, context):
                    state.reset_clean(reason="VERIFIED_LEGAL_REST")
                    
            elif event.activity == ActivityType.UNKNOWN:
                if event.gap_severity == GapSeverity.STRUCTURAL_BREAK:
                    state.reset_clean(reason="HEURISTIC_STRUCTURAL_BREAK")
                elif event.gap_severity == GapSeverity.HARD_GAP:
                    assessments.append(LegalAssessment(
                        continuity_state=ContinuityState.BROKEN_UNCERTAIN, severity=LegalSeverity.NONE,
                        accumulated_driving_minutes=state.continuous_driving, trajectory_confidence=state.trajectory_confidence,
                        trigger_event_id=event.event_id, state_reset_reason=state.last_state_reset_reason
                    ))
                elif event.gap_severity == GapSeverity.SOFT_GAP:
                    state.continuous_driving += event.duration_minutes

        if not assessments:
            assessments.append(LegalAssessment(
                continuity_state=ContinuityState.MAINTAINED, severity=LegalSeverity.NONE,
                accumulated_driving_minutes=state.continuous_driving, trajectory_confidence=state.trajectory_confidence,
                state_reset_reason=state.last_state_reset_reason
            ))
            
        return assessments

# ==============================================================================
# 5. UX TRANSLATOR LAYER
# ==============================================================================
class UXActionType(str, Enum):
    CONTINUE = "CONTINUE"
    PARK_IMMEDIATELY = "PARK_IMMEDIATELY"
    CONDITIONAL_ART12 = "CONDITIONAL_ART12"
    CORROBORATE_GAP = "CORROBORATE_GAP"

class DriverFeedback(BaseModel):
    ux_action: UXActionType
    status_color: str
    headline: str
    action_message: str
    legal_basis: List[str]
    detailed_explanation: str

class RiskTranslator:
    @staticmethod
    def map_to_ux(assessments: List[LegalAssessment]) -> DriverFeedback:
        worst = sorted(assessments, key=lambda a: (
            a.continuity_state == ContinuityState.BROKEN_VIOLATION,
            a.severity == LegalSeverity.VERY_SERIOUS,
            a.accumulated_driving_minutes
        ), reverse=True)[0]
        
        disclaimer = ("\n\nOSTRZEŻENIE: Wyjaśnienia stanowią interpretację danych i nie są wiążącą poradą prawną. "
                      "Ostateczna ocena należy do organu kontrolnego. System nie ponosi odpowiedzialności prawnej.")

        if worst.continuity_state == ContinuityState.MAINTAINED:
            return DriverFeedback(
                ux_action=UXActionType.CONTINUE, status_color="GREEN",
                headline="Brak stwierdzonych naruszeń 🟢",
                action_message="Aktualny blok jazdy jest zgodny z Art. 7.",
                legal_basis=["Rozporządzenie (WE) nr 561/2006, Art. 7"],
                detailed_explanation="Przeanalizowane dane są zgodne z wymogami ciągłości jazdy." + disclaimer
            )
            
        if worst.continuity_state == ContinuityState.BROKEN_VIOLATION and worst.trajectory_confidence > 0.8:
            return DriverFeedback(
                ux_action=UXActionType.PARK_IMMEDIATELY, status_color="RED",
                headline="Naruszenie przepisów Art. 7 🔴",
                action_message=f"Przekroczono limit jazdy o {worst.accumulated_driving_minutes - 270} min.",
                legal_basis=["Rozporządzenie (WE) nr 561/2006, Art. 7"],
                detailed_explanation="Zidentyfikowano naruszenie limitu 4,5h jazdy bez przepisowej przerwy." + disclaimer
            )
            
        elif worst.continuity_state == ContinuityState.BROKEN_VIOLATION and worst.trajectory_confidence <= 0.8:
            return DriverFeedback(
                ux_action=UXActionType.CONDITIONAL_ART12, status_color="ORANGE",
                headline="Procedura awaryjna (Art. 12) 🛡️",
                action_message="Dane wykazują przekroczenie. Jeśli zjazd był niemożliwy, przygotuj wydruk.",
                legal_basis=["Rozporządzenie (WE) nr 561/2006, Art. 12"],
                detailed_explanation="W sytuacji obiektywnej niemożności zjazdu, Art. 12 pozwala na odstępstwo. Sporządź odręczny opis na wydruku z tachografu." + disclaimer
            )
            
        else: 
            return DriverFeedback(
                ux_action=UXActionType.CORROBORATE_GAP, status_color="YELLOW",
                headline="Luka informacyjna 🟡",
                action_message="Wykryto brak danych. Zarejestruj wpis manualny.",
                legal_basis=["Rozporządzenie (UE) nr 165/2014, Art. 34 ust. 3"],
                detailed_explanation="Wykryto przerwę w rejestracji. Upewnij się, że posiadasz wpis manualny lub dokumentację odpoczynku." + disclaimer
            )

# ==============================================================================
# 6. GDPR-COMPLIANT AUDIT TRAIL
# ==============================================================================
class AuditLogger:
    @staticmethod
    def log_transaction(driver_id: str, assessments: List[LegalAssessment], ux_action: UXActionType):
        driver_pseudo_hmac = hmac.new(APP_SECRET_KEY, driver_id.encode('utf-8'), hashlib.sha256).hexdigest()
        state_string = "".join([f"{a.rule_reference}:{a.continuity_state}:{a.state_reset_reason}" for a in assessments])
        payload_hash = hashlib.sha256(state_string.encode('utf-8')).hexdigest()
        
        log_entry = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "driver_pseudo_hmac": driver_pseudo_hmac,
            "legal_state_hash": payload_hash,
            "decision_ux_action": ux_action.value,
            "kernel_version": KERNEL_VERSION,
            "kernel_build_id": KERNEL_BUILD_ID,
            "legal_policy_version": LEGAL_POLICY_VERSION
        }
        print(f"[SECURE AUDIT RECORD] {log_entry}")

# ==============================================================================
# 7. WEB SERVER BOUNDARY
# ==============================================================================
app = FastAPI(title="Defensive Compliance Assistant API")

class ScanRequest(BaseModel):
    driver_id: str
    applicability_context: ApplicabilityContext
    events: List[CanonicalEvent]

@app.post("/api/v1/analyze", response_model=DriverFeedback)
def analyze_scan(request: ScanRequest):
    patched_timeline = StrictTemporalValidator.enforce_physics(request.events)
    engine = Regulation561_Art7_Engine()
    legal_assessments = engine.evaluate(patched_timeline, request.applicability_context)
    ux_response = RiskTranslator.map_to_ux(legal_assessments)
    AuditLogger.log_transaction(request.driver_id, legal_assessments, ux_response.ux_action)
    return ux_response

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)