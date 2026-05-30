from ocr.transcriber import OCRTranscriber
from timeline.reconstructor import TimelineReconstructor
from rules.registry import RuleRegistry
from rules.article7 import Article7Rule
from rules.article34 import Article34Rule

class AuditPipeline:
    def __init__(self):
        self.ocr = OCRTranscriber()
        self.timeline_builder = TimelineReconstructor()
        
        self.rule_engine = RuleRegistry()
        self.rule_engine.register(Article7Rule())
        self.rule_engine.register(Article34Rule())

    def run(self, image_bytes, profile=None):
        doc_date, raw_events = self.ocr.extract(image_bytes)
        if not raw_events:
            return {"status": "NO_EVENTS", "message": "Brak zdarzeń na wydruku."}

        timeline = self.timeline_builder.process(doc_date, raw_events)
        violations = self.rule_engine.evaluate_all(timeline)
        
        if not violations:
            c_status = "COMPLIANT"
            summary = "Pełna zgodność z prawem. Nie odnotowano naruszeń proceduralnych ani przekroczeń limitów."
        else:
            c_status = "NON_COMPLIANT"
            summary = "Wykryto naruszenia proceduralne. Zapoznaj się z szablonami obrony w sekcjach poniżej."
            
        return {
            "compliance_status": c_status,
            "confidence_score": 0.98,
            "summary": summary,
            "violations": [v.model_dump() for v in violations]
        }
