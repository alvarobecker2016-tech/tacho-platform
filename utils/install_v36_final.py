import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FILES_TO_CREATE = {
    "domain/models.py": '''from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime
from domain.enums import EventType, Severity, RestType

class LegalCitation(BaseModel):
    article: str
    regulation: str = "Rozporządzenie (WE) nr 561/2006" # V36 Fix
    source: str = "Rozporządzenie (WE) nr 561/2006"
    official_reference: str = "Dz.U. L 102 z 11.4.2006"
    jurisdiction: str = "EU"

class RuleExecutionEvidence(BaseModel):
    calculation_steps: List[str] = Field(default_factory=list)
    involved_event_ids: List[str] = Field(default_factory=list)
    math_summary: str = ""

class Violation(BaseModel):
    rule_id: str
    citation: LegalCitation
    description: str
    explanation: str
    severity: Severity
    erru_class: str = "SI" # V36: ERRU Classification (MI/SI/VSI/MSI)
    estimated_fine_eur: int
    defense_strategy: Optional[str] = None
    defense_possible: bool = True
    execution_evidence: Optional[RuleExecutionEvidence] = None

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

class TimelineSegment(BaseModel):
    segment_id: str
    source: str
    events: List[TimelineEvent] = Field(default_factory=list)
    is_verified: bool = False
    segment_root_hash: str = ""

class EvidencePackage(BaseModel):
    package_id: str
    compliance_status: str
    violations: List[Violation]
    master_root_hash: str
''',

    "rules/article8.py": '''from typing import List
from datetime import timedelta
from domain.enums import EventType, Severity, RestType, SplitRestState
from domain.models import TimelineEvent, Violation, LegalCitation, DriverContext, LegalContext
from rules.base import BaseRule

class Article8Rule(BaseRule):
    """V36: Maszyna stanów dla Art 8 - odpoczynki dzienne (w tym split rest)."""
    def evaluate(self, timeline: List[TimelineEvent], context: DriverContext, legal_context: LegalContext) -> List[Violation]:
        violations = []
        shift_start = None
        split_state = SplitRestState.WAITING_FOR_3H
        
        for ev in timeline:
            if shift_start is None and ev.activity in [EventType.DRIVING, EventType.OTHER_WORK]:
                shift_start = ev.start
            
            if shift_start:
                # Weryfikacja okna 24h
                if ev.end > shift_start + timedelta(hours=24):
                    violations.append(Violation(
                        rule_id="ART8_DAILY", 
                        citation=LegalCitation(article="Art. 8 ust. 2"),
                        description="Przekroczenie okna 24h.",
                        explanation="Kierowca nie ukończył odpoczynku dziennego w wymaganym oknie.",
                        severity=Severity.HIGH, erru_class="SI", estimated_fine_eur=150
                    ))
                    shift_start = ev.start
                    
            if ev.legal_rest_type == RestType.SPLIT_DAILY_PART:
                if split_state == SplitRestState.WAITING_FOR_3H: split_state = SplitRestState.WAITING_FOR_9H
            elif ev.legal_rest_type in [RestType.REGULAR_DAILY, RestType.REGULAR_WEEKLY, RestType.REDUCED_WEEKLY]:
                shift_start = None; split_state = SplitRestState.WAITING_FOR_3H
            elif ev.legal_rest_type == RestType.REDUCED_DAILY:
                if split_state == SplitRestState.WAITING_FOR_9H:
                    shift_start = None; split_state = SplitRestState.WAITING_FOR_3H
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
                
                is_shift_start = (prev_ev is None or prev_ev.activity == EventType.UNKNOWN or prev_ev.duration >= 120)
                if is_shift_start and next_ev and next_ev.activity in [EventType.OTHER_WORK, EventType.DRIVING]:
                    violations.append(Violation(
                        rule_id="ART34", 
                        citation=LegalCitation(article="Art. 34 ust. 5", regulation="Rozp. 165/2014"),
                        description="Błąd selektora (15 min łóżka po logowaniu).",
                        explanation="Błędnie użyto selektora zamiast 'innej pracy'.",
                        severity=Severity.MEDIUM, erru_class="MI", estimated_fine_eur=50
                    ))
        return violations
'''
}

def create_structure():
    print("🚀 Instalacja V36 Final: ERRU & Legal Structures...")
    for filepath, content in FILES_TO_CREATE.items():
        with open(os.path.join(BASE_DIR, filepath), "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✅ Zaktualizowano: {filepath}")
    print("\n🎉 V36 Final gotowe. System posiada taryfikator ERRU i pełną spójność citacji.")

if __name__ == "__main__":
    create_structure()
