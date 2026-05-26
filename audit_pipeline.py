# =========================================================
# POCKET DGSA & TACHO
# ENTERPRISE COMPLIANCE AI ENGINE v7
# DETERMINISTIC LEGAL RUNTIME
# PRODUCTION READY CORE
# =========================================================

import base64
import hashlib
import json
import uuid
import time
import re

from enum import Enum

from datetime import (
    datetime,
    timedelta,
    timezone
)

from typing import (
    List,
    Optional,
    Dict
)

from pydantic import (
    BaseModel,
    Field,
    field_validator
)

from openai import OpenAI


# =========================================================
# CONFIG
# =========================================================

OPENAI_MODEL_VISION = "gpt-4o"

OPENAI_MODEL_FAST = "gpt-4o-mini"

CONFIDENCE_THRESHOLD = 0.80

MAX_CONTINUOUS_DRIVING_MINUTES = 270

MAX_DAILY_DRIVING_MINUTES = 540

MAX_WEEKLY_DRIVING_MINUTES = 3360

client = OpenAI()


# =========================================================
# ENUMS
# =========================================================

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


# =========================================================
# OCR STRUCTURES
# =========================================================

class OCRHeader(BaseModel):

    document_date: str

    timezone_hint: Optional[str] = "UTC"


class OCRTimelineEvent(BaseModel):

    start_time_raw: str

    end_time_raw: str

    activity: EventType

    confidence: float = Field(
        ge=0.0,
        le=1.0
    )

    @field_validator(
        "start_time_raw",
        "end_time_raw"
    )
    @classmethod
    def validate_time_format(
        cls,
        value
    ):

        pattern = r"^\d{2}:\d{2}$"

        if not re.match(pattern, value):

            raise ValueError(
                f"Invalid HH:MM format: {value}"
            )

        hours, minutes = map(
            int,
            value.split(":")
        )

        if hours > 23 or minutes > 59:

            raise ValueError(
                f"Invalid time: {value}"
            )

        return value


class OCRExtractionResult(BaseModel):

    driver_name: str

    card_number: str

    header: OCRHeader

    events: List[OCRTimelineEvent]

    overall_confidence: float


# =========================================================
# RULE METADATA
# =========================================================

class RuleMetadata(BaseModel):

    rule_id: str

    article: str

    regulation: str

    version: str

    country_scope: List[str]

    priority: int

    deterministic: bool = True


# =========================================================
# ENFORCEMENT PROFILE
# =========================================================

class EnforcementProfile(BaseModel):

    country: str

    authority: str

    tolerance_minutes: int

    fine_multiplier: float

    strict_mode: bool


GERMANY_PROFILE = EnforcementProfile(
    country="DE",
    authority="BALM",
    tolerance_minutes=1,
    fine_multiplier=1.3,
    strict_mode=True
)

POLAND_PROFILE = EnforcementProfile(
    country="PL",
    authority="ITD",
    tolerance_minutes=3,
    fine_multiplier=1.0,
    strict_mode=False
)


# =========================================================
# TIMELINE EVENT
# =========================================================

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


# =========================================================
# DRIVER CONTEXT
# =========================================================

class DriverStateContext(BaseModel):

    continuous_driving_minutes: int = 0

    daily_driving_minutes: int = 0

    weekly_driving_minutes: int = 0

    current_break_sequence: List[int] = []

    current_daily_rest_minutes: int = 0

    reduced_daily_rests_used: int = 0

    split_break_active: bool = False

    triggered_rules: List[str] = []

    last_event_time: Optional[datetime] = None

    current_week_number: Optional[int] = None


# =========================================================
# VIOLATION
# =========================================================

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


# =========================================================
# AUDIT TRACE
# =========================================================

class AuditTrace(BaseModel):

    audit_id: str

    started_at: datetime

    finished_at: Optional[datetime]

    ocr_latency_ms: Optional[float]

    rule_engine_latency_ms: Optional[float]

    legal_engine_latency_ms: Optional[float]

    total_execution_ms: Optional[float]

    model_vision: str

    model_fast: str

    rules_executed: int

    violations_detected: int


# =========================================================
# FINAL REPORT
# =========================================================

class AuditReport(BaseModel):

    audit_id: str

    created_at: datetime

    summary: str

    violations: List[Violation]

    total_risk_score: float

    compliance_status: str

    confidence_score: float

    trace: AuditTrace


# =========================================================
# UTILS
# =========================================================

def mask_sensitive_data(
    value: str
):

    return "[DANE UKRYTE]"


def generate_integrity_hash(
    start_time,
    end_time,
    activity,
    duration
):

    payload = (
        f"{start_time}"
        f"{end_time}"
        f"{activity}"
        f"{duration}"
    )

    return hashlib.sha256(
        payload.encode()
    ).hexdigest()


# =========================================================
# DATETIME RECONSTRUCTION
# =========================================================

class DateTimeReconstructor:

    @staticmethod
    def reconstruct(
        document_date: str,
        raw_events: List[OCRTimelineEvent]
    ) -> List[TimelineEvent]:

        events = []

        current_date = datetime.strptime(
            document_date,
            "%Y-%m-%d"
        )

        previous_start = None

        for raw_event in raw_events:

            sh, sm = map(
                int,
                raw_event.start_time_raw.split(":")
            )

            eh, em = map(
                int,
                raw_event.end_time_raw.split(":")
            )

            start_dt = current_date.replace(
                hour=sh,
                minute=sm,
                second=0,
                microsecond=0,
                tzinfo=timezone.utc
            )

            end_dt = current_date.replace(
                hour=eh,
                minute=em,
                second=0,
                microsecond=0,
                tzinfo=timezone.utc
            )

            # MIDNIGHT ROLLOVER

            if previous_start and start_dt < previous_start:

                current_date += timedelta(days=1)

                start_dt += timedelta(days=1)

                end_dt += timedelta(days=1)

            # END ROLLOVER

            if end_dt < start_dt:

                end_dt += timedelta(days=1)

            duration = int(
                (end_dt - start_dt).total_seconds() / 60
            )

            integrity_hash = generate_integrity_hash(
                start_dt,
                end_dt,
                raw_event.activity,
                duration
            )

            events.append(

                TimelineEvent(
                    event_id=str(uuid.uuid4()),
                    integrity_hash=integrity_hash,
                    start_time_utc=start_dt,
                    end_time_utc=end_dt,
                    activity=raw_event.activity,
                    duration_minutes=duration,
                    source="OCR_ENGINE",
                    confidence=raw_event.confidence,
                    created_at=datetime.now(
                        timezone.utc
                    )
                )
            )

            previous_start = start_dt

        return events


# =========================================================
# OCR ENGINE
# =========================================================

class OCREngine:

    def __init__(self):

        self.client = client

    def extract(
        self,
        image_bytes
    ) -> OCRExtractionResult:

        base64_image = base64.b64encode(
            image_bytes
        ).decode("utf-8")

        system_prompt = """
        Analyze tachograph printout.

        STRICT RULES:

        - Never invent timestamps
        - Never invent activities
        - Extract only visible evidence
        - Return HH:MM values only
        - Lower confidence if uncertain
        """

        response = self.client.beta.chat.completions.parse(

            model=OPENAI_MODEL_VISION,

            messages=[

                {
                    "role": "system",
                    "content": system_prompt
                },

                {
                    "role": "user",
                    "content": [

                        {
                            "type": "text",
                            "text": "Extract tachograph timeline."
                        },

                        {
                            "type": "image_url",
                            "image_url": {
                                "url": (
                                    f"data:image/jpeg;base64,"
                                    f"{base64_image}"
                                ),
                                "detail": "high"
                            }
                        }
                    ]
                }
            ],

            response_format=OCRExtractionResult,

            temperature=0
        )

        parsed = (
            response
            .choices[0]
            .message
            .parsed
        )

        parsed.driver_name = mask_sensitive_data(
            parsed.driver_name
        )

        parsed.card_number = mask_sensitive_data(
            parsed.card_number
        )

        return parsed


# =========================================================
# DRIVER STATE MACHINE
# =========================================================

class DriverStateMachine:

    def transition(
        self,
        context: DriverStateContext,
        event: TimelineEvent
    ):

        current_week = (
            event.start_time_utc.isocalendar()[1]
        )

        # WEEK RESET

        if (
            context.current_week_number
            and current_week != context.current_week_number
        ):

            context.weekly_driving_minutes = 0

        context.current_week_number = current_week

        # DRIVING

        if event.activity == EventType.DRIVING:

            context.continuous_driving_minutes += (
                event.duration_minutes
            )

            context.daily_driving_minutes += (
                event.duration_minutes
            )

            context.weekly_driving_minutes += (
                event.duration_minutes
            )

            # BREAK RESET

            context.current_break_sequence = []

        # BREAK

        elif event.activity == EventType.BREAK:

            context.current_break_sequence.append(
                event.duration_minutes
            )

            # FULL BREAK RESET

            if event.duration_minutes >= 45:

                context.continuous_driving_minutes = 0

                context.current_break_sequence = []

            # SPLIT BREAK 15 + 30

            elif event.duration_minutes >= 30:

                has_15_break = any(
                    b >= 15
                    for b in context.current_break_sequence[:-1]
                )

                if has_15_break:

                    context.continuous_driving_minutes = 0

                    context.current_break_sequence = []

        # REST

        elif event.activity == EventType.REST:

            context.current_daily_rest_minutes += (
                event.duration_minutes
            )

            # DAILY RESET

            if event.duration_minutes >= 540:

                context.daily_driving_minutes = 0

                context.continuous_driving_minutes = 0

                context.current_daily_rest_minutes = 0

                context.current_break_sequence = []

        # OTHER WORK / AVAILABILITY

        else:

            context.current_break_sequence = []

        context.last_event_time = (
            event.end_time_utc
        )

        return context


# =========================================================
# ART 7 RULE
# =========================================================

class Art7ContinuousDrivingRule:

    metadata = RuleMetadata(

        rule_id="ART7_CONTINUOUS_DRIVING",

        article="Art. 7",

        regulation="561/2006",

        version="1.0.0",

        country_scope=["EU"],

        priority=1
    )

    def evaluate(
        self,
        context: DriverStateContext,
        event: TimelineEvent,
        profile: EnforcementProfile
    ):

        violations = []

        rule_key = (
            f"{self.metadata.rule_id}_"
            f"{event.event_id}"
        )

        if rule_key in context.triggered_rules:

            return violations

        limit = (
            MAX_CONTINUOUS_DRIVING_MINUTES
            + profile.tolerance_minutes
        )

        if context.continuous_driving_minutes > limit:

            excess = (
                context.continuous_driving_minutes
                - MAX_CONTINUOUS_DRIVING_MINUTES
            )

            severity = (
                Severity.MEDIUM
                if excess <= 60
                else Severity.HIGH
            )

            base_fine = (
                100 if excess <= 60 else 250
            )

            final_fine = int(
                base_fine
                * profile.fine_multiplier
            )

            violations.append(

                Violation(
                    violation_id=str(uuid.uuid4()),
                    rule_id=self.metadata.rule_id,
                    article=self.metadata.article,
                    regulation=self.metadata.regulation,
                    description=(
                        f"Przekroczenie "
                        f"ciągłego czasu jazdy "
                        f"o {excess} minut."
                    ),
                    severity=severity,
                    estimated_fine_eur=final_fine,
                    confidence=0.95,
                    defense_possible=True,
                    defense_strategy=(
                        "Możliwe powołanie "
                        "na Art. 12 lub Art. 9 "
                        "w zależności od sytuacji."
                    ),
                    evidence_event_ids=[
                        event.event_id
                    ],
                    triggered_at=datetime.now(
                        timezone.utc
                    )
                )
            )

            context.triggered_rules.append(
                rule_key
            )

        return violations


# =========================================================
# RULE ENGINE
# =========================================================

class RuleEngine:

    def __init__(self):

        self.rules = [

            Art7ContinuousDrivingRule()
        ]

    def evaluate(
        self,
        timeline_events,
        profile
    ):

        violations = []

        state_machine = DriverStateMachine()

        context = DriverStateContext()

        for event in timeline_events:

            context = state_machine.transition(
                context,
                event
            )

            for rule in self.rules:

                result = rule.evaluate(
                    context,
                    event,
                    profile
                )

                violations.extend(result)

        return violations


# =========================================================
# LEGAL ENGINE
# =========================================================

class LegalEngine:

    def generate_report(
        self,
        violations,
        confidence_score,
        audit_trace
    ):

        if not violations:

            return AuditReport(

                audit_id=audit_trace.audit_id,

                created_at=datetime.now(
                    timezone.utc
                ),

                summary=(
                    "Brak wykrytych "
                    "naruszeń czasu jazdy."
                ),

                violations=[],

                total_risk_score=0.1,

                compliance_status="COMPLIANT",

                confidence_score=confidence_score,

                trace=audit_trace
            )

        # TEMPLATE-BASED REPORT
        # NO LEGAL HALLUCINATIONS

        summary_lines = []

        for violation in violations:

            summary_lines.append(

                f"- {violation.article} "
                f"({violation.regulation}) | "
                f"{violation.description}"
            )

        summary = "\n".join(
            summary_lines
        )

        return AuditReport(

            audit_id=audit_trace.audit_id,

            created_at=datetime.now(
                timezone.utc
            ),

            summary=summary,

            violations=violations,

            total_risk_score=min(
                len(violations) * 0.2,
                1.0
            ),

            compliance_status="NON_COMPLIANT",

            confidence_score=confidence_score,

            trace=audit_trace
        )


# =========================================================
# MAIN AUDIT PIPELINE
# =========================================================

class AuditPipeline:

    def __init__(self):

        self.ocr_engine = OCREngine()

        self.rule_engine = RuleEngine()

        self.legal_engine = LegalEngine()

    def run(
        self,
        image_bytes,
        profile=POLAND_PROFILE
    ):

        audit_id = str(uuid.uuid4())

        start_time = time.time()

        trace = AuditTrace(

            audit_id=audit_id,

            started_at=datetime.now(
                timezone.utc
            ),

            finished_at=None,

            ocr_latency_ms=0.0,

            rule_engine_latency_ms=0.0,

            legal_engine_latency_ms=0.0,

            total_execution_ms=0.0,

            model_vision=OPENAI_MODEL_VISION,

            model_fast=OPENAI_MODEL_FAST,

            rules_executed=1,

            violations_detected=0
        )

        # OCR

        ocr_start = time.time()

        ocr_result = (
            self.ocr_engine.extract(
                image_bytes
            )
        )

        trace.ocr_latency_ms = (
            time.time() - ocr_start
        ) * 1000

        # CONFIDENCE GATE

        if (
            ocr_result.overall_confidence
            < CONFIDENCE_THRESHOLD
        ):

            return {

                "status": "UNCERTAIN",

                "message": (
                    "Jakość dokumentu "
                    "jest zbyt niska."
                )
            }

        # TIMELINE

        timeline = (
            DateTimeReconstructor.reconstruct(
                ocr_result.header.document_date,
                ocr_result.events
            )
        )

        # RULE ENGINE

        rules_start = time.time()

        violations = (
            self.rule_engine.evaluate(
                timeline,
                profile
            )
        )

        trace.rule_engine_latency_ms = (
            time.time() - rules_start
        ) * 1000

        trace.violations_detected = (
            len(violations)
        )

        # LEGAL ENGINE

        legal_start = time.time()

        report = (
            self.legal_engine.generate_report(
                violations,
                ocr_result.overall_confidence,
                trace
            )
        )

        trace.legal_engine_latency_ms = (
            time.time() - legal_start
        ) * 1000

        # FINALIZE TRACE

        trace.total_execution_ms = (
            time.time() - start_time
        ) * 1000

        trace.finished_at = datetime.now(
            timezone.utc
        )

        report.trace = trace

        return report.model_dump()