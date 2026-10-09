import re
from typing import List, Sequence

from presidio_analyzer import (
    AnalyzerEngine,
    Pattern,
    PatternRecognizer,
    RecognizerRegistry,
)

from src.common.schema import PIIFinding
from src.detection.allowlist import ALLOWLIST
from src.detection.employee_id_recognizer import EmployeeIdRecognizer


ENTITY_MAPPING = {
    "PERSON": "PERSON_NAME",
    "EMAIL_ADDRESS": "EMAIL",
    "PHONE_NUMBER": "PHONE",
    "DATE_TIME": "DATE",
    "DATE": "DATE",
    "CREDIT_CARD": "CARD_NUMBER",
    "US_SSN": "SSN",
    "US_BANK_NUMBER": "ACCOUNT_NUMBER",
}

# Precompiled regex patterns for performance and thread safety
CARD_FALLBACK_PATTERN = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")
SSN_STRICT_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
DIGIT_ONLY_CODE_PATTERN = re.compile(r"^\d{5,6}$")

ADDRESS_PREFIX_PATTERN = re.compile(
    r"\b(?:home\s+address|residential\s+address|address)"
    r"\s*:\s*((?:[^\n.;]|\.(?=\S))+)",
    re.IGNORECASE,
)

# Anchor pattern: matches actual dates, months, year milestones, delimited formats, and timestamps
CALENDAR_ANCHOR_PATTERN = re.compile(
    r"\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b|"
    r"\b(?:19|20)\d{2}\b|"
    r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|"
    r"\b\d{1,2}:\d{2}(?::\d{2})?\s*(?:am|pm)?\b",
    re.IGNORECASE,
)

VAGUE_DATE_PATTERNS = [
    # Relative durations/counts (e.g., "in 2 days", "3 weeks ago", "a few hours", "over a month")
    re.compile(
        r"^(?:in\s+|within\s+|for\s+|over\s+)?(?:\d+|a|an|one|two|three|several|a\s+few|a\s+couple\s+of)\s+"
        r"(?:seconds?|minutes?|hours?|days?|weeks?|months?|quarters?|years?)(?:\s+ago)?$",
        re.IGNORECASE,
    ),
    # Relative anchor windows (e.g., "the past year", "over the last month", "this coming week")
    re.compile(
        r"^(?:over\s+|during\s+|throughout\s+|in\s+)?(?:the\s+)?(?:last|past|next|coming|this|previous)\s+"
        r"(?:second|minute|hour|day|week|month|quarter|year)$",
        re.IGNORECASE,
    ),
    # General non-calendar period references (e.g., "the day", "today", "yesterday", "tomorrow")
    re.compile(
        r"^(?:during\s+|throughout\s+)?(?:the\s+)?(?:day|night|morning|afternoon|evening|today|yesterday|tomorrow)$",
        re.IGNORECASE,
    ),
    # Recurrence intervals and generic frequencies
    re.compile(
        r"^(?:daily|weekly|monthly|quarterly|yearly|annually|hourly)$",
        re.IGNORECASE,
    ),
]

VAGUE_DATE_KEYWORDS = {
    "hours", "hour", "the day", "day",
    "the past year", "past year",
    "over a month", "a month",
    "quarterly", "daily", "weekly",
    "monthly", "yearly",
}

TEMPORAL_DURATION_WORDS = {
    "hour", "hours", "day", "days", "week", "weeks",
    "month", "months", "year", "years", "time", "period",
}

DATE_LABEL_OFFSETS = {
    "date of birth": "DATE_OF_BIRTH",
    "birth date": "DATE_OF_BIRTH",
    "dob": "DATE_OF_BIRTH",
    "born on": "DATE_OF_BIRTH",
    "date of joining": "DATE",
    "joining date": "DATE",
    "employment started on": "DATE",
    "meeting date": "DATE",
    "created date": "DATE",
}


def build_custom_recognizers() -> List[PatternRecognizer]:
    """Create recognizers for regional identifiers and contextual numbers."""
    return [
        PatternRecognizer(
            supported_entity="PAN",
            name="IndianPANRecognizer",
            patterns=[
                Pattern(
                    name="indian_pan_pattern",
                    regex=r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",
                    score=0.85,
                )
            ],
            context=["PAN", "permanent account number"],
        ),
        PatternRecognizer(
            supported_entity="AADHAAR",
            name="AadhaarRecognizer",
            patterns=[
                Pattern(
                    name="aadhaar_pattern",
                    regex=r"(?<!\d)(?:\d{4}[ -]?){2}\d{4}(?!\d)",
                    score=0.65,
                )
            ],
            context=["aadhaar", "uid", "unique identification number"],
        ),
        PatternRecognizer(
            supported_entity="PASSPORT",
            name="IndianPassportRecognizer",
            patterns=[
                Pattern(
                    name="indian_passport_pattern",
                    regex=r"\b[A-PR-WYa-pr-wy][0-9]{7}\b",
                    score=0.7,
                )
            ],
            context=["passport", "passport number", "passport no"],
        ),
        PatternRecognizer(
            supported_entity="PHONE_NUMBER",
            name="IndianPhoneRecognizer",
            patterns=[
                Pattern(
                    name="indian_mobile_pattern",
                    regex=r"(?<!\d)(?:\+91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\d)",
                    score=0.75,
                )
            ],
            context=["phone", "mobile", "contact", "telephone", "call"],
        ),
        PatternRecognizer(
            supported_entity="ACCOUNT_NUMBER",
            name="AccountNumberRecognizer",
            patterns=[
                Pattern(
                    name="account_number_pattern",
                    regex=r"(?<!\d)\d{8,18}(?!\d)",
                    score=0.45,
                )
            ],
            context=[
                "account number",
                "account no",
                "bank account",
                "a/c number",
                "a/c no",
            ],
        ),
        PatternRecognizer(
            supported_entity="SSN",
            name="SSNRecognizer",
            patterns=[
                Pattern(
                    name="ssn_pattern",
                    regex=r"\b\d{3}-\d{2}-\d{4}\b",
                    score=0.75,
                )
            ],
            context=["SSN", "social security number"],
        ),
    ]


class PIIDetector:
    def __init__(self):
        registry = RecognizerRegistry()
        registry.load_predefined_recognizers()
        registry.add_recognizer(EmployeeIdRecognizer())

        for recognizer in build_custom_recognizers():
            registry.add_recognizer(recognizer)

        self.analyzer = AnalyzerEngine(
            registry=registry,
            supported_languages=["en"],
        )

    @staticmethod
    def _spans_overlap(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
        """Evaluate if two half-open intervals [start, end) overlap."""
        return max(a_start, b_start) < min(a_end, b_end)

    @classmethod
    def _is_vague_date_phrase(cls, value: str) -> bool:
        """
        Reject vague durations, relative references, and non-specific time expressions
        even when Presidio captures surrounding prepositions or modifiers.
        """
        clean_val = " ".join(value.strip().casefold().split())

        if clean_val in VAGUE_DATE_KEYWORDS:
            return True

        if any(pattern.fullmatch(clean_val) for pattern in VAGUE_DATE_PATTERNS):
            return True

        # Catch boundary variations where duration nouns appear without calendar anchors
        if not CALENDAR_ANCHOR_PATTERN.search(clean_val):
            tokens = set(clean_val.split())
            if (tokens & TEMPORAL_DURATION_WORDS) and len(tokens) <= 4:
                return True

        return False

    @staticmethod
    def _has_context(
        text: str, start: int, end: int, terms: Sequence[str], window: int = 60
    ) -> bool:
        """
        Check whether specified context terms occur near a span using
        strict word boundaries to prevent substring collisions.
        """
        context_window = text[max(0, start - window):min(len(text), end + window)]
        escaped_terms = "|".join(re.escape(term) for term in terms)
        return bool(re.search(rf"\b(?:{escaped_terms})\b", context_window, re.IGNORECASE))

    @staticmethod
    def _classify_date(text: str, start: int) -> str:
        """Classify a date as DOB only when supported by preceding context."""
        context = text[max(0, start - 60):start].casefold()

        nearest_position = -1
        classification = "DATE"

        for label, entity_type in DATE_LABEL_OFFSETS.items():
            pos = context.rfind(label)
            if pos > nearest_position:
                nearest_position = pos
                classification = entity_type

        return classification

    @staticmethod
    def _passes_luhn(value: str) -> bool:
        """Validate candidate digit string with standard Luhn checksum."""
        digits = [int(char) for char in value if char.isdigit()]
        if not 13 <= len(digits) <= 19:
            return False

        total = 0
        for index, digit in enumerate(reversed(digits)):
            if index % 2 == 1:
                digit *= 2
                if digit > 9:
                    digit -= 9
            total += digit

        return total % 10 == 0

    @classmethod
    def _detect_labelled_addresses(cls, text: str) -> List[PIIFinding]:
        """Find candidate address spans following explicit address prefixes."""
        findings = []

        for match in ADDRESS_PREFIX_PATTERN.finditer(text):
            address = match.group(1).strip().rstrip(" .")
            if not address or not re.search(r"[A-Za-z0-9]", address):
                continue

            orig_val = match.group(1)
            leading_ws = len(orig_val) - len(orig_val.lstrip())
            start = match.start(1) + leading_ws
            end = start + len(address)

            findings.append(
                PIIFinding(
                    entity_type="HOME_ADDRESS",
                    text=address,
                    start=start,
                    end=end,
                    confidence=0.85,
                    detector="AddressContextRecognizer",
                )
            )

        return findings

    def detect(self, text: str) -> List[PIIFinding]:
        """Detect PII findings, applying context gates, checksums, and deconfliction."""
        if not isinstance(text, str):
            raise TypeError("text must be a string")

        results = self.analyzer.analyze(text=text, language="en")
        findings: List[PIIFinding] = []

        for result in results:
            raw_type = result.entity_type
            value = text[result.start:result.end]
            norm_val = value.strip().casefold()

            # Ignore contact labels falsely classified as person names
            if raw_type == "PERSON" and norm_val in {
                "mobile", "phone", "telephone", "email", "contact", "address"
            }:
                continue

            # Suppress vague temporal expressions and standalone numeric codes
            if raw_type in ("DATE", "DATE_TIME", "TIME"):
                if self._is_vague_date_phrase(value):
                    continue
                if DIGIT_ONLY_CODE_PATTERN.fullmatch(value.strip()):
                    continue

            # Filter out non-passport US driver's licenses
            if raw_type == "US_DRIVER_LICENSE":
                continue

            # Skip unanchored single-token locations (addresses handled explicitly)
            if raw_type == "LOCATION":
                continue

            entity_type = ENTITY_MAPPING.get(raw_type, raw_type)

            # Contextual classification for dates (e.g., DOB)
            if raw_type in ("DATE", "DATE_TIME"):
                entity_type = self._classify_date(text, result.start)

            # Context verification for sensitive identifiers
            if entity_type == "AADHAAR" and not self._has_context(
                text, result.start, result.end, ("aadhaar", "uid", "unique identification number")
            ):
                continue

            if entity_type == "PASSPORT" and not self._has_context(
                text, result.start, result.end, ("passport", "passport number", "passport no")
            ):
                continue

            if entity_type == "ACCOUNT_NUMBER" and not self._has_context(
                text, result.start, result.end, ("account number", "account no", "bank account", "a/c number", "a/c no")
            ):
                continue

            # Strict US SSN formatting check
            if entity_type == "SSN":
                if not SSN_STRICT_PATTERN.fullmatch(value.strip()):
                    continue

            # Reject card candidates failing the Luhn checksum
            if entity_type == "CARD_NUMBER" and not self._passes_luhn(value):
                continue

            # Suppress person names detected directly near date labels
            if raw_type == "PERSON":
                nearby = text[max(0, result.start - 20):min(len(text), result.end + 20)].casefold()
                if any(lbl in nearby for lbl in ("birth date", "date of birth", "date of joining", "joining date")):
                    continue

            # Allowlist lookup
            clean_token = " ".join(norm_val.split())
            allowed = {" ".join(item.split()).casefold() for item in ALLOWLIST.get(entity_type, set())}
            if clean_token in allowed:
                continue

            findings.append(
                PIIFinding(
                    entity_type=entity_type,
                    text=value,
                    start=result.start,
                    end=result.end,
                    confidence=result.score,
                    detector=result.recognition_metadata.get("recognizer_name", "Presidio"),
                )
            )

        # Detect full labelled addresses
        findings.extend(self._detect_labelled_addresses(text))

        # Card Fallback: Extract Luhn-valid cards missed by Presidio
        card_spans = [(f.start, f.end) for f in findings if f.entity_type == "CARD_NUMBER"]
        for match in CARD_FALLBACK_PATTERN.finditer(text):
            candidate = match.group(0)
            m_start, m_end = match.start(), match.end()

            if not self._passes_luhn(candidate):
                continue

            # Interval overlap check
            if any(self._spans_overlap(m_start, m_end, c_start, c_end) for c_start, c_end in card_spans):
                continue

            card_finding = PIIFinding(
                entity_type="CARD_NUMBER",
                text=candidate,
                start=m_start,
                end=m_end,
                confidence=0.75,
                detector="LuhnValidatedCardFallback",
            )
            findings.append(card_finding)
            card_spans.append((m_start, m_end))

        # SSN Fallback: Detect strictly formatted SSNs without requiring context
        for match in SSN_STRICT_PATTERN.finditer(text):
            start, end = match.span()

            if any(
                finding.entity_type == "SSN"
                and self._spans_overlap(start, end, finding.start, finding.end)
                for finding in findings
            ):
                continue

            findings.append(
                PIIFinding(
                    entity_type="SSN",
                    text=match.group(),
                    start=start,
                    end=end,
                    confidence=0.75,
                    detector="StrictSSNFallback",
                )
            )

        # Conflict Resolution:
        # 1. Strip URLs that fall inside emails
        # 2. Strip dates that overlap with phone numbers
        email_spans = [(f.start, f.end) for f in findings if f.entity_type == "EMAIL"]
        phone_spans = [(f.start, f.end) for f in findings if f.entity_type == "PHONE"]

        resolved_findings: List[PIIFinding] = []
        for item in findings:
            if item.entity_type == "URL" and any(
                e_start <= item.start and item.end <= e_end for e_start, e_end in email_spans
            ):
                continue

            if item.entity_type in ("DATE", "DATE_OF_BIRTH") and any(
                self._spans_overlap(item.start, item.end, p_start, p_end) for p_start, p_end in phone_spans
            ):
                continue

            resolved_findings.append(item)

        # Deduplicate identical findings by (entity_type, start, end)
        unique_findings: List[PIIFinding] = []
        seen = set()
        for item in resolved_findings:
            key = (item.entity_type, item.start, item.end)
            if key not in seen:
                seen.add(key)
                unique_findings.append(item)

        # Sort in natural document order
        unique_findings.sort(key=lambda item: (item.start, item.end))
        return unique_findings