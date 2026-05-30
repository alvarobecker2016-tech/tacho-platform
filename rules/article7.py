from typing import List
from domain.enums import EventType, Severity
from domain.models import TimelineEvent, Violation
from rules.base import BaseRule

class Article7Rule(BaseRule):
    LIMIT = 270

    def evaluate(self, timeline: List[TimelineEvent]) -> List[Violation]:
        violations = []
        continuous_driving = 0
        
        for ev in timeline:
            if ev.activity == EventType.DRIVING:
                continuous_driving += ev.duration
            elif ev.activity in [EventType.BREAK, EventType.REST] and ev.duration >= 45:
                continuous_driving = 0
            elif ev.activity == EventType.UNKNOWN:
                continuous_driving += ev.duration
            
            if continuous_driving > self.LIMIT:
                exc = continuous_driving - self.LIMIT
                violations.append(Violation(
                    rule_id="ART7",
                    article="Art. 7",
                    regulation="561/2006",
                    description=f"Przekroczenie ciągłej jazdy o {exc} min.",
                    explanation=f"Zgromadzono {continuous_driving} min jazdy bez wymaganej, minimum 45-minutowej przerwy.",
                    severity=Severity.HIGH if exc > 60 else Severity.MEDIUM,
                    estimated_fine_eur=50 + (exc * 1),
                    defense_possible=True
                ))
                continuous_driving = 0
                
        return violations
