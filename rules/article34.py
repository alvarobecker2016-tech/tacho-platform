from typing import List
from domain.enums import EventType, Severity
from domain.models import TimelineEvent, Violation
from rules.base import BaseRule

class Article34Rule(BaseRule):
    def evaluate(self, timeline: List[TimelineEvent]) -> List[Violation]:
        violations = []
        
        for idx, ev in enumerate(timeline):
            if ev.activity == EventType.REST and 0 < ev.duration <= 15:
                prev_ev = timeline[idx-1] if idx > 0 else None
                next_ev = timeline[idx+1] if idx + 1 < len(timeline) else None
                
                is_shift_start = False
                if prev_ev is None or prev_ev.activity == EventType.UNKNOWN:
                    is_shift_start = True
                elif prev_ev.activity == EventType.REST and prev_ev.duration >= 120:
                    is_shift_start = True
                    
                if is_shift_start and next_ev and next_ev.activity in [EventType.OTHER_WORK, EventType.DRIVING]:
                    doc_d = ev.start.strftime('%d.%m.%Y')
                    s_time = ev.start.strftime('%H:%M')
                    e_time = ev.end.strftime('%H:%M')
                    
                    expl = f"""**Błąd formalny - niewłaściwe użycie selektora.**
> **Data i czas zdarzenia:** {doc_d}, godz. {s_time} – {e_time}
> **Prawidłowa czynność:** Inna praca (młotki)
> **Wyjaśnienie:** Omyłkowe użycie selektora / błąd logowania. Zamiast 'innej pracy', tachograf zarejestrował {ev.duration} min odpoczynku.
> **Podstawa prawna:** Korekta wg Art. 34 ust. 3 Rozp. (UE) 165/2014.
> *[Podpis kierowcy]*"""

                    violations.append(Violation(
                        rule_id="ART34",
                        article="Art. 34 ust. 5 lit. b",
                        regulation="165/2014",
                        description=f"Błąd selektora ({ev.duration} min łóżka tuż po logowaniu karty).",
                        explanation=expl,
                        severity=Severity.MEDIUM,
                        estimated_fine_eur=50,
                        defense_strategy="Bardzo silna obrona. Opisz wydruk wg szablonu."
                    ))
        return violations
