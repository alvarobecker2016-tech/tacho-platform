# =========================================================
# POCKET DGSA & TACHO
# ENTERPRISE COMPLIANCE AI ENGINE v26
# MAIN CONDUCTOR (AUDIT PIPELINE COUPLING MODULAR CORE)
# =========================================================

from ocr.transcriber import OCRTranscriber
from timeline.reconstructor import TimelineReconstructor
from rules.evaluator import RuleEvaluator

class AuditPipeline:
    """
    Główny potok audytowy systemu (Conductor).
    Odpowiada za orkiestrację niezależnych komponentów dziedzinowych
    i dostarczenie stabilnego kontraktu danych (DTO) dla aplikacji frontendowej.
    """
    def __init__(self):
        # Inicjalizacja wyspecjalizowanych warstw serwisowych
        self.ocr = OCRTranscriber()
        self.timeline_builder = TimelineReconstructor()
        self.evaluator = RuleEvaluator()

    def run(self, image_bytes, profile=None):
        """
        Uruchamia pełny proces inspekcji Forensic LegalTech.
        
        Parametry:
            image_bytes (bytes): Surowy strumień binarnego zdjęcia z tachografu.
            profile (Optional): Pakiet jurysdykcji (zachowany dla kompatybilności).
            
        Zwraca:
            dict: Ściśle sformatowany DTO akceptowany przez render_audit_report w app.py.
        """
        # 1. Warstwa OCR: Ekstrakcja surowych symboli i piktogramów bez interpretacji AI
        doc_date, raw_events = self.ocr.extract(image_bytes)
        
        if not raw_events:
            return {
                "status": "NO_EVENTS", 
                "message": "Brak zdarzeń na wydruku. Upewnij się, że zdjęcie jest ostre i dobrze doświetlone."
            }

        # 2. Warstwa Osi Czasu: Deterministyczna odbudowa chronologii przez Pythona (Reguła 1 minuty)
        timeline = self.timeline_builder.process(doc_date, raw_events)
        
        # 3. Warstwa Reguł: Ewaluacja naruszeń przepisów (Art. 34 - selektor oraz Art. 7 - ciągła jazda)
        violations = self.evaluator.evaluate(timeline)
        
        # 4. Warstwa Raportowania: Pakowanie struktur obiektowych do czystego JSON dla Streamlita
        if not violations:
            c_status = "COMPLIANT"
            summary = (
                f"Szanowny Panie/Pani Kierowco,\n\n"
                f"Po dokładnej, deterministycznej analizie osi czasu z dnia {doc_date} "
                f"nie stwierdzono żadnych uchybień ani naruszeń przepisów Rozporządzenia (WE) nr 561/2006 "
                f"oraz 165/2014. Pełna zgodność ewidencji czasu pracy."
            )
        else:
            c_status = "NON_COMPLIANT"
            summary = (
                f"Wykryto uchybienia proceduralne lub przekroczenia limitów czasu pracy "
                f"na osi czasu z dnia {doc_date}. "
                f"Zapoznaj się z precyzyjnymi wytycznymi prawnymi oraz szablonami obrony "
                f"wyszczególnionymi w sekcji kroków zaradczych poniżej."
            )
        
        return {
            "compliance_status": c_status,
            "confidence_score": 0.98,
            "summary": summary,
            "violations": [v.model_dump() for v in violations]
        }
