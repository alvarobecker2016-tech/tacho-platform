from typing import List
from domain.enums import EventType, Severity
from domain.models import TimelineEvent, Violation

class RuleEvaluator:
    def evaluate(self, timeline: List[dict]) -> List[Violation]:
        violations = []
        continuous_driving = 0
        
        for idx, ev in enumerate(timeline):
            # ---------------------------------------------------------
            # ART. 34: BŁĄD SELEKTORA (1 do 15 min łóżka po zalogowaniu)
            # ---------------------------------------------------------
            if ev["activity"] == EventType.REST and 0 < ev["duration"] <= 15:
                prev_ev = timeline[idx-1] if idx > 0 else None
                next_ev = timeline[idx+1] if idx + 1 < len(timeline) else None
                
                is_shift_start = False
                if prev_ev is None or prev_ev["activity"] == EventType.UNKNOWN:
                    is_shift_start = True
                elif prev_ev["activity"] == EventType.REST and prev_ev["duration"] >= 120:
                    is_shift_start = True
                    
                if is_shift_start and next_ev and next_ev["activity"] in [EventType.OTHER_WORK, EventType.DRIVING]:
                    s_time = ev["start"].strftime("%H:%M")
                    e_time = ev["end"].strftime("%H:%M")
                    doc_d = ev["start"].strftime('%d.%m.%Y')
                    
                    explanation = f"""**Błąd formalny - niewłaściwe użycie selektora grup czasowych:**
Zamiast 'innej pracy' (młotki) w celu przygotowania pojazdu, urządzenie zarejestrowało odpoczynek. 

**SZABLON WPISU DO PRZEPISANIA NA ODWROCIE WYDRUKU:**
> **Data i czas zdarzenia:** {doc_d}, godz. {s_time} – {e_time}
> **Prawidłowa czynność:** Inna praca (młotki)
> **Wyjaśnienie:** Omyłkowe użycie selektora grup czasowych / błąd zapisu podczas logowania karty. Zamiast innej pracy, tachograf zarejestrował {ev["duration"]} min odpoczynku.
> **Podstawa prawna:** Korekta zapisu zgodnie z Art. 34 ust. 3 Rozporządzenia (UE) 165/2014.
> *[Czytelny podpis kierowcy]*"""

                    violations.append(Violation(
                        rule_id="ART34",
                        article="Art. 34 ust. 5 lit. b",
                        regulation="165/2014",
                        description=f"Zarejestrowano błąd formalny selektora ({ev['duration']} min łóżka tuż po zalogowaniu karty).",
                        explanation=explanation,
                        severity=Severity.MEDIUM,
                        estimated_fine_eur=50,
                        defense_strategy="Bardzo silna obrona. Opisz wydruk odręcznie wg podanego szablonu, podpisz i zachowaj na 28 dni."
                    ))

            # ---------------------------------------------------------
            # ART. 7: CIĄGŁA JAZDA (Zabezpieczenie przed przepracowaniem)
            # ---------------------------------------------------------
            if ev["activity"] == EventType.DRIVING:
                continuous_driving += ev["duration"]
            elif ev["activity"] == EventType.BREAK and ev["duration"] >= 45:
                continuous_driving = 0
            
            if continuous_driving > 270:
                exc = continuous_driving - 270
                violations.append(Violation(
                    rule_id="ART7",
                    article="Art. 7",
                    regulation="561/2006",
                    description=f"Przekroczenie ciągłej jazdy o {exc} min.",
                    explanation=f"Zgromadzono {continuous_driving} min jazdy bez 45 min przerwy.",
                    severity=Severity.HIGH if exc > 60 else Severity.MEDIUM,
                    estimated_fine_eur=50 + (exc * 1)
                ))
                continuous_driving = 0

        return violations
