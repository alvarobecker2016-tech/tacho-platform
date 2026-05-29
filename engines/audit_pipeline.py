# =========================================================
# engines/audit_pipeline.py - GŁÓWNY POTOK (PIPELINE)
# =========================================================
import time
import uuid
import base64
from datetime import datetime, timezone
from typing import List

from models.domain import (
    EnforcementProfile,
    AuditTrace,
    AuditReport,
    Violation,
    OCRExtractionResult,
    TimelineEvent,
    DriverStateContext
)
from config import (
    client, 
    OPENAI_MODEL_VISION, 
    OPENAI_MODEL_FAST, 
    CONFIDENCE_THRESHOLD
)
from utils.helpers import mask_sensitive_data, DateTimeReconstructor
from utils.state_machine import DriverStateMachine

# =========================================================
# TWARDE PRAWO - AKTYWNE FILARY
# =========================================================
from rules.art7_continuous_driving import Art7ContinuousDrivingRule
from rules.art8_daily_rest import Art8DailyRestRule       # <-- WŁĄCZONO ART. 8!
from rules.art6_daily_driving import Art6DrivingLimitsRule

# =========================================================
# OCR ENGINE
# =========================================================
class OCREngine:
    def __init__(self):
        self.client = client

    def extract(self, image_bytes) -> OCRExtractionResult:
        base64_image = base64.b64encode(image_bytes).decode("utf-8")
        
        system_prompt = """
        Analyze tachograph printout.
        STRICT RULES:
        - Never invent timestamps
        - Never invent activities
        - Extract only visible evidence
        - Return HH:MM values only
        - Extract document date separately
        - Lower confidence if uncertain
        """

        response = self.client.beta.chat.completions.parse(
            model=OPENAI_MODEL_VISION,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": [
                    {"type": "text", "text": "Extract tachograph timeline."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}", "detail": "high"}}
                ]}
            ],
            response_format=OCRExtractionResult,
            temperature=0
        )

        parsed = response.choices[0].message.parsed
        parsed.driver_name = mask_sensitive_data(parsed.driver_name)
        parsed.card_number = mask_sensitive_data(parsed.card_number)
        return parsed

# =========================================================
# RULE ENGINE
# =========================================================
class RuleEngine:
    def __init__(self):
        # Pełny arsenał prawny gotowy do strzału
        self.rules = [
            Art7ContinuousDrivingRule(),
            Art8DailyRestRule(),          # <-- Silnik załadował odpoczynki
            Art6DrivingLimitsRule()
        ]
        self.rules.sort(key=lambda r: r.metadata.priority)

    def evaluate(
        self,
        timeline_events: List[TimelineEvent],
        profile: EnforcementProfile
    ) -> List[Violation]:
        
        violations = []
        state_machine = DriverStateMachine()
        context = DriverStateContext()

        for event in timeline_events:
            context = state_machine.transition(context, event)
            
            for rule in self.rules:
                result = rule.evaluate(context, event, profile)
                if hasattr(result, 'violations'):
                    violations.extend(result.violations)

        return violations

# =========================================================
# RISK ENGINE
# =========================================================
class RiskEngine:
    @staticmethod
    def calculate(violations: List[Violation]) -> float:
        if not violations:
            return 0.1
        score = len(violations) * 0.2
        return min(score, 1.0)

# =========================================================
# LEGAL ENGINE
# =========================================================
class LegalEngine:
    def __init__(self):
        self.client = client

    def generate_report(
        self,
        violations: List[Violation],
        confidence_score: float,
        audit_trace: AuditTrace
    ) -> AuditReport:

        if not violations:
            return AuditReport(
                audit_id=audit_trace.audit_id,
                created_at=datetime.now(timezone.utc),
                summary="Brak wykrytych naruszeń czasu pracy. Pełna zgodność (Compliant).",
                violations=[],
                total_risk_score=0.1,
                compliance_status="COMPLIANT",
                confidence_score=confidence_score,
                trace=audit_trace
            )

        system_prompt = """
        Wygeneruj profesjonalne podsumowanie prawne.
        Nie wymyślaj przepisów.
        Bazuj wyłącznie na podanym JSON.
        """

        response = self.client.chat.completions.create(
            model=OPENAI_MODEL_FAST,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": str([v.model_dump() for v in violations])}
            ],
            temperature=0
        )

        return AuditReport(
            audit_id=audit_trace.audit_id,
            created_at=datetime.now(timezone.utc),
            summary=response.choices[0].message.content,
            violations=violations,
            total_risk_score=RiskEngine.calculate(violations),
            compliance_status="NON_COMPLIANT",
            confidence_score=confidence_score,
            trace=audit_trace
        )

# =========================================================
# GŁÓWNA KLASA ORKIESTRUJĄCA
# =========================================================
class AuditPipeline:
    def __init__(self):
        self.ocr_engine = OCREngine()
        self.rule_engine = RuleEngine()
        self.legal_engine = LegalEngine()

    def run(self, image_bytes, profile):
        audit_id = str(uuid.uuid4())
        total_start = time.time()

        trace = AuditTrace(
            audit_id=audit_id,
            started_at=datetime.now(timezone.utc),
            finished_at=None,
            ocr_latency_ms=0.0,
            reconstruction_latency_ms=0.0,
            rule_engine_latency_ms=0.0,
            legal_engine_latency_ms=0.0,
            total_execution_ms=0.0,
            model_vision=OPENAI_MODEL_VISION,
            model_fast=OPENAI_MODEL_FAST,
            rules_executed=len(self.rule_engine.rules),
            violations_detected=0
        )

        # 1. OCR
        ocr_start = time.time()
        ocr_result = self.ocr_engine.extract(image_bytes)
        trace.ocr_latency_ms = (time.time() - ocr_start) * 1000

        if ocr_result.overall_confidence < CONFIDENCE_THRESHOLD:
            return {"status": "UNCERTAIN", "message": "Jakość dokumentu zbyt niska."}

        # 2. Rekonstrukcja Czasu (Bezpieczna z helpers.py)
        recon_start = time.time()
        
        # Bezpieczne pobranie daty dokumentu
        doc_date = ocr_result.header.document_date if hasattr(ocr_result, 'header') and hasattr(ocr_result.header, 'document_date') else ""
        
        # Bezpieczne pobranie listy zdarzeń
        events_list = getattr(ocr_result, 'events', [])
        if not events_list and hasattr(ocr_result, 'timeline'):
            events_list = ocr_result.timeline
            
        timeline = DateTimeReconstructor.reconstruct(doc_date, events_list)
        trace.reconstruction_latency_ms = (time.time() - recon_start) * 1000

        # 3. Maszyna Prawna (Rule Engine)
        rule_start = time.time()
        violations = self.rule_engine.evaluate(timeline, profile)
        trace.rule_engine_latency_ms = (time.time() - rule_start) * 1000
        trace.violations_detected = len(violations)

        # 4. Generowanie Raportu (Legal Engine)
        legal_start = time.time()
        report = self.legal_engine.generate_report(violations, ocr_result.overall_confidence, trace)
        trace.legal_engine_latency_ms = (time.time() - legal_start) * 1000

        # Zakończenie audytu
        trace.total_execution_ms = (time.time() - total_start) * 1000
        trace.finished_at = datetime.now(timezone.utc)
        report.trace = trace

        return report.model_dump()
