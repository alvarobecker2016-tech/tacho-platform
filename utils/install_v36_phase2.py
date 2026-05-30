import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FILES_TO_CREATE = {
    "domain/enums.py": '''from enum import Enum

class EventType(str, Enum):
    DRIVING = "DRIVING"
    BREAK = "BREAK"
    REST = "REST"
    OTHER_WORK = "OTHER_WORK"
    AVAILABILITY = "AVAILABILITY"
    UNKNOWN = "UNKNOWN"
    FERRY_TRAIN = "FERRY_TRAIN"

class RestType(str, Enum):
    NONE = "NONE"
    REGULAR_DAILY = "REGULAR_DAILY"
    REDUCED_DAILY = "REDUCED_DAILY"
    SPLIT_DAILY_PART = "SPLIT_DAILY_PART"
    REGULAR_WEEKLY = "REGULAR_WEEKLY"
    REDUCED_WEEKLY = "REDUCED_WEEKLY"

class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class UnknownPolicy(str, Enum):
    STRICT = "STRICT"
    NEUTRAL = "NEUTRAL"
    DRIVER_FRIENDLY = "DRIVER_FRIENDLY"

class SplitRestState(str, Enum):
    WAITING_FOR_3H = "WAITING_FOR_3H"
    WAITING_FOR_9H = "WAITING_FOR_9H"

class ShiftState(str, Enum):
    OFF_DUTY = "OFF_DUTY"
    ON_DUTY = "ON_DUTY"
    FERRY_INTERRUPTION = "FERRY_INTERRUPTION"
''',

    "domain/models.py": '''from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime
from domain.enums import EventType, Severity, RestType, ShiftState

class LegalCitation(BaseModel):
    article: str
    source: str = "Rozporządzenie (WE) nr 561/2006"
    official_reference: str = "Dz.U. L 102 z 11.4.2006"
    jurisdiction: str = "EU"

class RuleExecutionEvidence(BaseModel):
    calculation_steps: List[str] = Field(default_factory=list)
    involved_event_ids: List[str] = Field(default_factory=list)
    math_summary: str = ""

class GNSSPosition(BaseModel):
    timestamp: datetime
    latitude: float
    longitude: float
    accuracy: float
    is_border_crossing: bool = False

class TachographFault(BaseModel):
    fault_code: str
    timestamp: datetime
    description: str

class TimelineEvent(BaseModel):
    event_id: str
    integrity_hash: str
    parent_hash: str
    start: datetime
    end: datetime
    duration: int
    activity: EventType
    legal_rest_type: RestType = RestType.NONE
    confidence: float
    pictogram_raw: str
    gnss_position: Optional[GNSSPosition] = None

class TimelineSegment(BaseModel):
    segment_id: str
    source: str
    events: List[TimelineEvent] = Field(default_factory=list)
    faults: List[TachographFault] = Field(default_factory=list)
    is_verified: bool = False
    segment_root_hash: str = ""

class CompensationDebt(BaseModel):
    debt_hours: float
    created_at: datetime
    deadline_date: datetime
    repaid: bool = False
    repayment_event_id: Optional[str] = None

# V36 Phase 2: Doba Pracownicza wyciągnięta przez LegalPeriodEngine
class LegalWorkPeriod(BaseModel):
    shift_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    total_driving_mins: int = 0
    total_working_mins: int = 0
    touched_night_window: bool = False
    events_included: List[str] = Field(default_factory=list)

# V36 Phase 2: Rozszerzony Driver Context
class DriverContext(BaseModel):
    card_id: str
    historical_segments: List[TimelineSegment] = Field(default_factory=list)
    hotel_receipts: List[str] = Field(default_factory=list)
    border_crossings: List[GNSSPosition] = Field(default_factory=list)
    compensation_debts: List[CompensationDebt] = Field(default_factory=list)
    erru_history: List[str] = Field(default_factory=list)
    employer_context: str = "UNKNOWN_COMPANY"

# V36 Phase 2: Globalny Kontekst Prawny
class LegalContext(BaseModel):
    jurisdiction: str = "EU"
    inspection_country: str = "PL"
    enforce_erru: bool = True
    enforce_mobility_package: bool = True

class Violation(BaseModel):
    rule_id: str
    citation: LegalCitation
    description: str
    explanation: str
    severity: Severity
    estimated_fine_eur: int
    defense_strategy: Optional[str] = None
    defense_possible: bool = True
    execution_evidence: Optional[RuleExecutionEvidence] = None

class EvidenceManifest(BaseModel):
    manifest_id: str
    engine_version: str
    ruleset_version: str
    legal_snapshot: str = "EU_561_2006_DIR_2002_15_EC"
    generated_at: datetime
    driver_id: str
    segment_count: int
    master_root_hash: str
    digital_signature: Optional[str] = None

class AuditTrace(BaseModel):
    audit_id: str
    engine_version: str = "V36"
    started_at: datetime
    finished_at: Optional[datetime] = None
    rules_executed: int = 0
    violations_detected: int = 0
    timeline_reconstruction_score: float = 0.0
    rule_execution_trace: Dict[str, str] = Field(default_factory=dict)

class EvidencePackage(BaseModel):
    package_id: str
    manifest: EvidenceManifest
    compliance_status: str
    confidence_score: float
    timeline_segments: List[TimelineSegment]
    violations: List[Violation]
    audit_trace: AuditTrace
''',

    "timeline/period_engine.py": '''from typing import List, Dict
from domain.enums import EventType
from domain.models import TimelineEvent, LegalWorkPeriod

class LegalPeriodEngine:
    """
    V36 Phase 2: Silnik rozwiązujący problem rolowanych okien i zmian pracowniczych.
    Zastępuje twarde wyszukiwanie odpoczynków na osi czasu.
    """
    def extract_shifts(self, timeline: List[TimelineEvent]) -> List[LegalWorkPeriod]:
        shifts = []
        current_shift = None

        for ev in timeline:
            if current_shift is None and ev.activity in [EventType.DRIVING, EventType.OTHER_WORK]:
                current_shift = LegalWorkPeriod(shift_id=f"shift_{ev.event_id}", start_time=ev.start)

            if current_shift:
                current_shift.events_included.append(ev.event_id)
                current_shift.end_time = ev.end
                
                if ev.activity == EventType.DRIVING:
                    current_shift.total_driving_mins += ev.duration
                elif ev.activity == EventType.OTHER_WORK:
                    current_shift.total_working_mins += ev.duration

                # Check window 00:00 - 04:00
                if ev.start.hour < 4 or ev.end.hour < 4:
                    current_shift.touched_night_window = True

                # Zakończenie zmiany uelastycznione (mock maszyny stanów pauz)
                if ev.activity == EventType.REST and ev.duration >= 540:
                    shifts.append(current_shift)
                    current_shift = None

        if current_shift:
            shifts.append(current_shift)
            
        return shifts

    def extract_iso_weeks(self, timeline: List[TimelineEvent]) -> Dict[str, List[TimelineEvent]]:
        weeks = {}
        for ev in timeline:
            y, w, _ = ev.start.isocalendar()
            key = f"{y}-W{w:02d}"
            if key not in weeks:
                weeks[key] = []
            weeks[key].append(ev)
        return weeks
''',

    "rules/base.py": '''from abc import ABC, abstractmethod
from typing import List
from domain.models import TimelineEvent, Violation, DriverContext, LegalContext

class BaseRule(ABC):
    @abstractmethod
    def evaluate(self, timeline: List[TimelineEvent], context: DriverContext, legal_context: LegalContext) -> List[Violation]:
        pass
''',

    "legal/directive_2002_15_ec.py": '''from typing import List
from domain.enums import Severity
from domain.models import TimelineEvent, Violation, LegalCitation, RuleExecutionEvidence, DriverContext, LegalContext
from timeline.period_engine import LegalPeriodEngine
from rules.base import BaseRule

class WorkingTimeRule(BaseRule):
    MAX_NIGHT_SHIFT_WORK_MINS = 10 * 60

    def __init__(self):
        self.period_engine = LegalPeriodEngine()

    def evaluate(self, timeline: List[TimelineEvent], context: DriverContext, legal_context: LegalContext) -> List[Violation]:
        violations = []
        shifts = self.period_engine.extract_shifts(timeline)
        
        for shift in shifts:
            total_work = shift.total_driving_mins + shift.total_working_mins
            
            if shift.touched_night_window and total_work > self.MAX_NIGHT_SHIFT_WORK_MINS:
                exc_mins = total_work - self.MAX_NIGHT_SHIFT_WORK_MINS
                exc_h = round(exc_mins / 60.0, 1)
                
                evidence = RuleExecutionEvidence(
                    calculation_steps=[
                        f"Wykryto pracę w porze nocnej na zmianie startującej {shift.start_time}.",
                        f"Zsumowano czas pracy (Jazda+Młotki): {total_work} min."
                    ],
                    involved_event_ids=shift.events_included,
                    math_summary=f"Praca: {total_work}m > Limit Nocny: 600m"
                )
                
                violations.append(Violation(
                    rule_id="DIR_2002_15_NIGHT",
                    citation=LegalCitation(article="Art. 7", source="Dyrektywa 2002/15/WE"),
                    description=f"Przekroczenie 10h pracy przy zmianie nocnej o {exc_h}h.",
                    explanation="Kierowca wykonywał pracę w porze nocnej, co narzuca bezwzględny limit 10h pracy na dobę.",
                    severity=Severity.CRITICAL if exc_h > 2 else Severity.HIGH,
                    estimated_fine_eur=300 + int(exc_h * 100),
                    execution_evidence=evidence
                ))
        return violations
''',

    "rules/article6.py": '''from typing import List
from datetime import datetime
from domain.enums import EventType, Severity
from domain.models import TimelineEvent, Violation, LegalCitation, DriverContext, LegalContext
from rules.base import BaseRule
from timeline.period_engine import LegalPeriodEngine

class Article6Rule(BaseRule):
    WEEKLY_LIMIT_MINS = 56 * 60
    FORTNIGHT_LIMIT_MINS = 90 * 60

    def __init__(self):
        self.period_engine = LegalPeriodEngine()

    def _is_consecutive_iso_week(self, w1_str: str, w2_str: str) -> bool:
        y1, wk1 = map(int, w1_str.replace("-W", "-").split("-"))
        y2, wk2 = map(int, w2_str.replace("-W", "-").split("-"))
        d1 = datetime.fromisocalendar(y1, wk1, 1)
        d2 = datetime.fromisocalendar(y2, wk2, 1)
        return (d2 - d1).days == 7

    def evaluate(self, timeline: List[TimelineEvent], context: DriverContext, legal_context: LegalContext) -> List[Violation]:
        violations = []
        weeks_data = self.period_engine.extract_iso_weeks(timeline)
        weeks = sorted(weeks_data.keys())
        weekly_driving = {w: sum(ev.duration for ev in weeks_data[w] if ev.activity == EventType.DRIVING) for w in weeks}
        
        for i, week in enumerate(weeks):
            driving_mins = weekly_driving[week]
            if driving_mins > self.WEEKLY_LIMIT_MINS:
                exc_h = round((driving_mins - self.WEEKLY_LIMIT_MINS) / 60, 1)
                violations.append(Violation(
                    rule_id="ART6_WEEKLY", citation=LegalCitation(article="Art. 6 ust. 2"),
                    description=f"Przekroczenie tyg. czasu jazdy o {exc_h}h (Tydzień {week}).",
                    explanation=f"Czas prowadzenia wyniósł {round(driving_mins/60, 1)}h.",
                    severity=Severity.CRITICAL if exc_h > 4 else Severity.HIGH,
                    estimated_fine_eur=150 + int(exc_h * 50), defense_possible=False
                ))
            if i > 0:
                prev_week = weeks[i-1]
                if self._is_consecutive_iso_week(prev_week, week):
                    fortnight_mins = driving_mins + weekly_driving[prev_week]
                    if fortnight_mins > self.FORTNIGHT_LIMIT_MINS:
                        exc_h = round((fortnight_mins - self.FORTNIGHT_LIMIT_MINS) / 60, 1)
                        violations.append(Violation(
                            rule_id="ART6_FORTNIGHT", citation=LegalCitation(article="Art. 6 ust. 3"),
                            description=f"Przekroczenie dwutygodniowego czasu jazdy o {exc_h}h.",
                            explanation=f"Suma jazdy: {prev_week} i {week} wyniosła {round(fortnight_mins/60, 1)}h.",
                            severity=Severity.CRITICAL if exc_h > 5 else Severity.HIGH,
                            estimated_fine_eur=200 + int(exc_h * 50), defense_possible=False
                        ))
        return violations
''',

    "rules/article7.py": '''from typing import List
from domain.enums import EventType, Severity, UnknownPolicy
from domain.models import TimelineEvent, Violation, LegalCitation, RuleExecutionEvidence, DriverContext, LegalContext
from rules.base import BaseRule

class BreakFragment:
    def __init__(self, duration: int, event_id: str):
        self.duration = duration
        self.event_id = event_id

class Article7Rule(BaseRule):
    LIMIT = 270 

    def __init__(self, policy: UnknownPolicy = UnknownPolicy.NEUTRAL):
        self.policy = policy

    def evaluate(self, timeline: List[TimelineEvent], context: DriverContext, legal_context: LegalContext) -> List[Violation]:
        violations = []
        continuous_driving = 0
        break_fragments: List[BreakFragment] = []
        driving_event_ids = []
        
        for ev in timeline:
            if ev.activity == EventType.DRIVING:
                continuous_driving += ev.duration
                driving_event_ids.append(ev.event_id)
            elif ev.activity in [EventType.BREAK, EventType.REST]:
                if ev.duration >= 45:
                    continuous_driving = 0
                    break_fragments.clear()
                    driving_event_ids.clear()
                elif ev.duration >= 15:
                    break_fragments.append(BreakFragment(ev.duration, ev.event_id))
                    has_15 = False; valid_sequence = False
                    for bf in break_fragments:
                        if bf.duration >= 15 and not has_15: has_15 = True
                        elif has_15 and bf.duration >= 30: valid_sequence = True; break
                    if valid_sequence:
                        continuous_driving = 0
                        break_fragments.clear()
                        driving_event_ids.clear()
                        
            elif ev.activity == EventType.UNKNOWN and self.policy == UnknownPolicy.STRICT:
                continuous_driving += ev.duration
                driving_event_ids.append(ev.event_id)
            
            if continuous_driving > self.LIMIT:
                exc_mins = continuous_driving - self.LIMIT
                sev = Severity.CRITICAL if exc_mins > 120 else Severity.HIGH
                fine = 250 + (exc_mins * 3)

                evidence = RuleExecutionEvidence(
                    calculation_steps=[f"Suma ciągłej jazdy: {continuous_driving}m"],
                    involved_event_ids=list(driving_event_ids),
                    math_summary=f"Total: {continuous_driving}m > 270m"
                )

                violations.append(Violation(
                    rule_id="ART7", citation=LegalCitation(article="Art. 7"),
                    description=f"Przekroczenie ciągłej jazdy o {exc_mins} min.",
                    explanation=f"Zgromadzono {continuous_driving} min jazdy bez 45-minutowej przerwy.",
                    severity=sev, estimated_fine_eur=fine, defense_possible=True,
                    execution_evidence=evidence
                ))
                continuous_driving = 0
                break_fragments.clear()
                driving_event_ids.clear()
                
        return violations
''',

    "rules/article8.py": '''from typing import List
from datetime import timedelta
from domain.enums import EventType, Severity, RestType, SplitRestState
from domain.models import TimelineEvent, Violation, LegalCitation, DriverContext, LegalContext
from rules.base import BaseRule

class Article8Rule(BaseRule):
    def evaluate(self, timeline: List[TimelineEvent], context: DriverContext, legal_context: LegalContext) -> List[Violation]:
        violations = []
        shift_start = None
        split_state = SplitRestState.WAITING_FOR_3H
        
        for ev in timeline:
            if shift_start is None and ev.activity in [EventType.DRIVING, EventType.OTHER_WORK]:
                shift_start = ev.start
                split_state = SplitRestState.WAITING_FOR_3H
                continue
                
            if shift_start:
                if ev.end > shift_start + timedelta(hours=24):
                    overtime_hours = round((ev.end - (shift_start + timedelta(hours=24))).total_seconds() / 3600, 1)
                    violations.append(Violation(
                        rule_id="ART8_DAILY", citation=LegalCitation(article="Art. 8 ust. 2"),
                        description=f"Brak odpoczynku dziennego. Przekroczono okno 24h o {overtime_hours}h.",
                        explanation="Kierowca nie ukończył wymaganych 9h (lub 3h+9h) przed upływem 24h.",
                        severity=Severity.HIGH, estimated_fine_eur=150 + int(overtime_hours * 50), defense_possible=True
                    ))
                    shift_start = ev.start
                    split_state = SplitRestState.WAITING_FOR_3H
                    
            if ev.legal_rest_type == RestType.SPLIT_DAILY_PART:
                if split_state == SplitRestState.WAITING_FOR_3H: split_state = SplitRestState.WAITING_FOR_9H
            elif ev.legal_rest_type in [RestType.REGULAR_DAILY, RestType.REGULAR_WEEKLY, RestType.REDUCED_WEEKLY]:
                shift_start = None
                split_state = SplitRestState.WAITING_FOR_3H
            elif ev.legal_rest_type == RestType.REDUCED_DAILY:
                shift_start = None
                split_state = SplitRestState.WAITING_FOR_3H
                    
        return violations
''',

    "rules/article8_weekly.py": '''from typing import List
from datetime import timedelta
from domain.enums import EventType, Severity, RestType
from domain.models import TimelineEvent, Violation, LegalCitation, DriverContext, LegalContext
from rules.base import BaseRule

class Article8WeeklyRule(BaseRule):
    LIMIT_HOURS = 144
    
    def evaluate(self, timeline: List[TimelineEvent], context: DriverContext, legal_context: LegalContext) -> List[Violation]:
        violations = []
        if not timeline: return violations
        last_weekly_rest_end = timeline[0].start 
        
        for ev in timeline:
            if ev.legal_rest_type in [RestType.REGULAR_WEEKLY, RestType.REDUCED_WEEKLY]:
                last_weekly_rest_end = ev.end
                continue
            if last_weekly_rest_end and ev.activity in [EventType.DRIVING, EventType.OTHER_WORK]:
                if ev.start > last_weekly_rest_end + timedelta(hours=self.LIMIT_HOURS):
                    overtime_hours = round((ev.start - (last_weekly_rest_end + timedelta(hours=self.LIMIT_HOURS))).total_seconds() / 3600, 1)
                    violations.append(Violation(
                        rule_id="ART8_WEEKLY_LIMIT", citation=LegalCitation(article="Art. 8 ust. 6"),
                        description=f"Przekroczono 6 dób roboczych o {overtime_hours}h.",
                        explanation="Brak rozpoczęcia odpoczynku tygodniowego w limicie 144h.",
                        severity=Severity.CRITICAL, estimated_fine_eur=250 + int(overtime_hours * 25), defense_possible=True
                    ))
                    last_weekly_rest_end = ev.start 
        return violations
''',

    "rules/article34.py": '''from typing import List
from domain.enums import EventType, Severity
from domain.models import TimelineEvent, Violation, LegalCitation, DriverContext, LegalContext
from rules.base import BaseRule

class Article34Rule(BaseRule):
    def evaluate(self, timeline: List[TimelineEvent], context: DriverContext, legal_context: LegalContext) -> List[Violation]:
        violations = []
        for idx, ev in enumerate(timeline):
            if ev.activity in [EventType.REST, EventType.BREAK] and 0 < ev.duration <= 15:
                prev_ev = timeline[idx-1] if idx > 0 else None
                next_ev = timeline[idx+1] if idx + 1 < len(timeline) else None
                
                is_shift_start = False
                if prev_ev is None or prev_ev.activity == EventType.UNKNOWN: is_shift_start = True
                elif prev_ev.activity in [EventType.REST, EventType.BREAK] and prev_ev.duration >= 120: is_shift_start = True
                    
                if is_shift_start and next_ev and next_ev.activity in [EventType.OTHER_WORK, EventType.DRIVING]:
                    violations.append(Violation(
                        rule_id="ART34", citation=LegalCitation(article="Art. 34 ust. 5", regulation="165/2014"),
                        description=f"Błąd selektora ({ev.duration} min łóżka tuż po logowaniu).",
                        explanation="Zamiast 'innej pracy', tachograf zarejestrował odpoczynek.",
                        severity=Severity.MEDIUM, estimated_fine_eur=50, defense_strategy="Korekta manualna."
                    ))
        return violations
''',

    "rules/registry.py": '''from typing import List, Tuple, Dict
from domain.models import TimelineEvent, Violation, DriverContext, LegalContext
from rules.base import BaseRule

class RuleRegistry:
    def __init__(self):
        self._rules: List[BaseRule] = []

    def register(self, rule: BaseRule):
        self._rules.append(rule)

    def evaluate_all(self, timeline: List[TimelineEvent], context: DriverContext, legal_context: LegalContext) -> Tuple[List[Violation], Dict[str, str]]:
        all_violations = []
        execution_trace = {}
        for rule in self._rules:
            rule_name = rule.__class__.__name__
            rule_violations = rule.evaluate(timeline, context, legal_context)
            if rule_violations: all_violations.extend(rule_violations)
            execution_trace[rule_name] = "FAIL" if rule_violations else "PASS"
        return all_violations, execution_trace
''',

    "audit_pipeline.py": '''import uuid
from typing import List
from rules.registry import RuleRegistry
from rules.article6 import Article6Rule
from rules.article7 import Article7Rule
from rules.article8 import Article8Rule
from rules.article8_weekly import Article8WeeklyRule
from rules.article34 import Article34Rule
from legal.directive_2002_15_ec import WorkingTimeRule
from domain.models import DriverContext, LegalContext, TimelineEvent, Violation
from domain.enums import UnknownPolicy

class AuditPipeline:
    def __init__(self):
        self.rule_engine = RuleRegistry()
        self.rule_engine.register(WorkingTimeRule()) # V36: Praca nocna (Dyrektywa 2002/15/WE)
        self.rule_engine.register(Article6Rule())
        self.rule_engine.register(Article7Rule(policy=UnknownPolicy.NEUTRAL))
        self.rule_engine.register(Article8Rule())
        self.rule_engine.register(Article8WeeklyRule())
        self.rule_engine.register(Article34Rule())

    def run_rules_only(self, timeline: List[TimelineEvent], context: DriverContext, legal_context: LegalContext) -> List[Violation]:
        violations, _ = self.rule_engine.evaluate_all(timeline, context, legal_context)
        return violations
'''
}

def create_structure():
    print("🚀 Instalacja V36 Phase 2: Legal Period Engine & Context Expansion...")
    directories = ["domain", "timeline", "rules", "legal"]
    for directory in directories:
        os.makedirs(os.path.join(BASE_DIR, directory), exist_ok=True)
        init_path = os.path.join(BASE_DIR, directory, "__init__.py")
        if not os.path.exists(init_path):
            with open(init_path, "w", encoding="utf-8") as f: f.write("")

    for filepath, content in FILES_TO_CREATE.items():
        with open(os.path.join(BASE_DIR, filepath), "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✅ Nadpisano/Utworzono: {filepath}")
        
    print("\n🎉 Zakończono! V36 Phase 2 wdrożone pomyślnie.")

if __name__ == "__main__":
    create_structure()
