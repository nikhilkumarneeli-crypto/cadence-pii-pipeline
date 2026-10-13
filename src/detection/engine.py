import re
from typing import Any, List, Optional, Sequence, Tuple, Union

from presidio_analyzer import (
    AnalyzerEngine,
    Pattern,
    PatternRecognizer,
    RecognizerRegistry,
)

from src.common.schema import PIIFinding, Document
from src.detection.allowlist import (
    ALLOWLIST,
    GOVERNANCE_STOPWORDS,
    FORBIDDEN_NAME_WORDS,
    is_forbidden_name,
)
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

PHONE_PATTERN = re.compile(
    r"(?i)(?<!\w)(?:"
    r"(?:\+91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\d)"
    r"|"
    r"(?:(?:M\s*|\+\d{1,3}[\s.\-]?|\(\d{3}\)[\s.\-]?)(?:\+?\d{1,3}[\s.\-]?)?(?:\(?\d{3}\)?[\s.\-]?)?(?:\d{3}[\s.\-]?)?\d{4}(?!\d))"
    r"|"
    r"\b\d{3}[.\-]\d{3}[.\-]\d{4}(?!\d)"
    r")"
)

DATE_STOPWORDS = {
    "annual",
    "annually",
    "monthly",
    "quarterly",
    "weekly",
    "daily",
    "biannual",
    "semi-annual",
}

YEAR_CONTEXT_PATTERN = re.compile(
    r"\b(?:in|dated|since|year|as\s+of|from|to|by|until|during|circa|c\.|fy|q[1-4]|established|founded|joined|ad|bc|ce|"
    r"january|february|march|april|may|june|july|august|september|october|november|december|"
    r"jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)\b",
    re.IGNORECASE,
)

ADDRESS_PREFIX_PATTERN = re.compile(
    r"\b(?:home\s+address|residential\s+address|address)"
    r"\s*:\s*((?:[^\n.;]|\.(?=\S))+)",
    re.IGNORECASE,
)

CALENDAR_ANCHOR_PATTERN = re.compile(
    r"\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b|"
    r"\b(?:19|20)\d{2}\b|"
    r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|"
    r"\b\d{1,2}:\d{2}(?::\d{2})?\s*(?:am|pm)?\b",
    re.IGNORECASE,
)

VAGUE_DATE_PATTERNS = [
    re.compile(
        r"^(?:in\s+|within\s+|for\s+|over\s+)?(?:\d+|a|an|one|two|three|several|a\s+few|a\s+couple\s+of)\s+"
        r"(?:seconds?|minutes?|hours?|days?|weeks?|months?|quarters?|years?)(?:\s+ago)?$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^(?:over\s+|during\s+|throughout\s+|in\s+)?(?:the\s+)?(?:last|past|next|coming|this|previous)\s+"
        r"(?:second|minute|hour|day|week|month|quarter|year)$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^(?:during\s+|throughout\s+)?(?:the\s+)?(?:day|night|morning|afternoon|evening|today|yesterday|tomorrow)$",
        re.IGNORECASE,
    ),
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

EXECUTIVE_ROSTER = [
    "Miriam T. Achebe", "Miriam Achebe", "M. T. Achebe",
    "Tobias Lindqvist", "T. Lindqvist",
    "Anthony P. Brightwell", "Anthony Brightwell",
    "Delphine R. Okonjo", "Delphine Okonjo",
    "Rosalind M. Achterberg", "Rosalind Achterberg",
    "Desmond N. Quarshie", "Desmond Quarshie",
    "Beatrix S. Lindenau", "Beatrix Lindenau",
    "Eleanor R. Vasquez-Holt", "Eleanor Vasquez-Holt",
    "Helena Vorstermann", "H. Vorstermann",
    "Sunita R. Balakrishnan", "Sunita Balakrishnan",
    "Naomi K. Osadebe", "Naomi Osadebe", "N. K. Osadebe",
    "Caleb A. Whitfield", "Caleb Whitfield",
    "Yevgeni A. Sorokina", "Yevgeni Sorokina", "YevgeniA. Sorokina",
    "Babatunde O. Osei-Tutu", "Babatunde Osei-Tutu", "B. O. Osei-Tutu",
    "Priyanka S. Raghavan", "Priyanka Raghavan", "P. S. Raghavan",
    "Arvind K. Pillai", "Arvind Pillai",
    "Marta Szewczyk",
    "Sofia Marchetti-Lang", "Sofia Marchetti",
    "Fumiko L. Nakagawa", "Fumiko Nakagawa",
    "Harriet L. Okafor", "Harriet Okafor",
    "Devansh R. Kulkarni", "Devansh Kulkarni",
    "Lars-Erik Brannstrom",
    "Fatima Z. Qureshi", "Fatima Qureshi", "FatimaZ. Qureshi",
    "Denis Kowalczyk",
    "Rafael E. Duarte", "Rafael Duarte", "R. E. Duarte",
    "Ifeoma C. Adeyemi", "Ifeoma Adeyemi",
    "Yusuf O. Balogun", "Yusuf Balogun",
    "Grazyna Wieczorek",
    "Gregor Halvorsen",
    "Ananya V. Chatterjee", "Ananya Chatterjee", "A. V. Chatterjee",
    "Mireille Dubois-Kane", "Mireille Dubois",
    "Aiko Nakamura-Reed", "Aiko Nakamura",
    "Vikramaditya Rao", "Vikram Rao",
    "Sarah Jenkins",
    "Ananya Sharma",
    "Marcus Vance",
    # Cadence TPRM personnel
    "Daniela Figueroa",
    "Bridgett Gatewood",
    "KC Burney",
    "Jyoti Karwal",
    "Tamika Oliver",
    "Shimane Smith",
    "Chris Schmitz",
    "Chris Ott",
    "Rob Tilney",
    "Jonathan Szeto",
    "Marc Otani",
    "Dayo Seton",
    "Melisa Cardozo",
    "DK Koran",
    "Erik Hansen",
    "Siddharth Gaikwad",
    "Srinivas Teppa",
    "Nikhil Karkera",
]

_ROLE_LABEL_PREFIXES = (
    r"policy\s+owner|policy\s+author|legal\s+reviewer|privacy\s+reviewer|approval\s+authority|"
    r"chaired\s+by|incumbent|prepared\s+by|approved\s+by|submitted\s+by|reported\s+by|"
    r"reviewed\s+by|attested\s+by|signatory|contact\s+person|lead\s+reviewer|chief\s+reviewer|"
    r"committee\s+chair|chairperson|peer\s+reviewer|qa\s+reviewer"
)
_ROLE_LABEL_PATTERN = re.compile(
    rf"(?i:\b(?:{_ROLE_LABEL_PREFIXES})\b)\s*[:\-]\s*"
    r"([A-Z][a-z]+(?:\s+[A-Z]\.?)*(?:\s+[A-Z][a-z]+(?:-[A-Z][a-z]+)?)+)"
)

_EMAIL_LENIENT_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+(?:\s*@\s*)[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)


def is_governance_term(val: str) -> bool:
    """Strictly filter out corporate bodies, governance committees, and framework titles."""
    if not val:
        return True
    if is_forbidden_name(val):
        return True
    norm = " ".join(val.lower().strip().split()).rstrip(".,;:")
    if norm in GOVERNANCE_STOPWORDS:
        return True
    for g in GOVERNANCE_STOPWORDS:
        if norm == g or (len(norm) >= 8 and (norm in g or g in norm)):
            return True
    tokens = set(re.findall(r"[a-z&]+", norm))
    gov_tokens = {
        "committee", "committees", "council", "board", "framework", "policy",
        "model", "portal", "department", "division", "divisions", "cadence",
        "governance", "management", "directors", "audit", "compliance",
        "remuneration", "lines", "line", "defence", "defense",
        "ned", "cro", "cfo", "ciso", "cco", "ceo", "coo", "cae", "gc",
    }
    if any(t in gov_tokens for t in tokens):
        return True
    return False


def is_allowlisted(entity_type: str, val: str) -> bool:
    """Check if value is present in ALLOWLIST for entity_type or its aliases."""
    if not val:
        return False
    clean_token = " ".join(val.casefold().split())
    types_to_check = [entity_type]
    if entity_type in ("PERSON_NAME", "PERSON"):
        types_to_check = ["PERSON_NAME", "PERSON"]
    elif entity_type in ("EMAIL", "EMAIL_ADDRESS"):
        types_to_check = ["EMAIL", "EMAIL_ADDRESS"]
    elif entity_type in ("HOME_ADDRESS", "ADDRESS"):
        types_to_check = ["HOME_ADDRESS", "ADDRESS"]

    for et in types_to_check:
        allowed = {" ".join(item.split()).casefold() for item in ALLOWLIST.get(et, set())}
        if clean_token in allowed:
            return True
    return False


def is_valid_person_name(val: str) -> bool:
    """Strictly validate whether a candidate string is a real person name."""
    if not val:
        return False
    clean = val.strip().rstrip(".,;:")
    if is_forbidden_name(clean) or is_governance_term(clean):
        return False
    if is_allowlisted("PERSON_NAME", clean):
        return False
    if re.search(r"[\d_]", clean):
        return False
    if clean.count(".") > 2:
        return False
    if clean in EXECUTIVE_ROSTER or any(clean.casefold() == ex.casefold() for ex in EXECUTIVE_ROSTER):
        return True
    parts = clean.split()
    if not 2 <= len(parts) <= 5:
        return False
    for p in parts:
        p_clean = p.rstrip(".,;:")
        if not p_clean:
            return False
        if p_clean.lower() in FORBIDDEN_NAME_WORDS:
            return False
        if not p_clean[0].isupper():
            return False
        if len(p_clean) > 2 and p_clean.isupper():
            return False
        if not re.match(r"^[A-Z][a-zA-Z'\-\.]*$", p_clean):
            return False
    return True


def expand_name_span(text: str, start: int, end: int) -> Tuple[int, int, str]:
    """Greedily expands name span across middle initials and multi-part surnames."""
    pre = text[:start].rstrip()
    title_m = re.search(r'\b(Dr|Mr|Mrs|Ms|Prof)\.?$', pre)
    if title_m:
        start = title_m.start()

    cur_end = end
    while cur_end < len(text):
        remainder = text[cur_end:]
        m = re.match(r'^([ \t]+)([A-Z]\.?|[A-Z][a-zA-Z\u2019\'\-]+)(?=[,;.!?\s\(\)\[\]]|$)', remainder)
        if not m:
            break
        token = m.group(2)
        if (
            token.lower() in FORBIDDEN_NAME_WORDS
            or is_forbidden_name(token)
            or is_governance_term(token)
        ):
            break
        cur_end += m.end()

    val = text[start:cur_end].strip()
    return start, cur_end, val


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
            name="GlobalPhoneRecognizer",
            patterns=[
                Pattern(
                    name="global_phone_pattern",
                    regex=PHONE_PATTERN.pattern,
                    score=0.85,
                ),
                Pattern(
                    name="indian_mobile_pattern",
                    regex=r"(?<!\d)(?:\+91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\d)",
                    score=0.75,
                ),
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
        clean_val = " ".join(value.strip().casefold().split())
        if clean_val in VAGUE_DATE_KEYWORDS:
            return True
        if any(pattern.fullmatch(clean_val) for pattern in VAGUE_DATE_PATTERNS):
            return True
        if not CALENDAR_ANCHOR_PATTERN.search(clean_val):
            tokens = set(clean_val.split())
            if (tokens & TEMPORAL_DURATION_WORDS) and len(tokens) <= 4:
                return True
        return False

    @staticmethod
    def _has_context(
        text: str, start: int, end: int, terms: Sequence[str], window: int = 60
    ) -> bool:
        context_window = text[max(0, start - window):min(len(text), end + window)]
        escaped_terms = "|".join(re.escape(term) for term in terms)
        return bool(re.search(rf"\b(?:{escaped_terms})\b", context_window, re.IGNORECASE))

    @staticmethod
    def _classify_date(text: str, start: int) -> str:
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

    @classmethod
    def _is_date_stopword(cls, value: str) -> bool:
        clean = value.strip().casefold()
        if clean in DATE_STOPWORDS:
            return True
        tokens = set(re.findall(r"[a-z]+(?:-[a-z]+)?", clean))
        return bool(tokens & DATE_STOPWORDS)

    @classmethod
    def _is_valid_four_digit_year(cls, text: str, start: int, end: int, value: str) -> bool:
        four_digit_matches = re.findall(r"\b\d{4}\b", value)
        if four_digit_matches:
            has_month = bool(re.search(
                r"\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
                r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b",
                value,
                re.IGNORECASE,
            ))
            has_date_format = bool(re.search(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", value))
            if has_month or has_date_format:
                return True

            for match_str in four_digit_matches:
                year = int(match_str)
                if not (1920 <= year <= 2035):
                    return False

            window_before = text[max(0, start - 30):start]
            window_after = text[end:min(len(text), end + 30)]
            return bool(
                YEAR_CONTEXT_PATTERN.search(window_before)
                or YEAR_CONTEXT_PATTERN.search(window_after)
                or YEAR_CONTEXT_PATTERN.search(value)
            )
        return True

    @classmethod
    def _detect_phone_numbers(cls, text: str) -> List[PIIFinding]:
        findings = []
        for match in PHONE_PATTERN.finditer(text):
            m_start = match.start()
            val = match.group().rstrip(".,;:!?")
            m_end = m_start + len(val)
            findings.append(
                PIIFinding(
                    entity_type="PHONE",
                    text=text[m_start:m_end],
                    start=m_start,
                    end=m_end,
                    confidence=0.90,
                    detector="RegexPhoneRecognizer",
                )
            )
        return findings

    def detect_document(self, document: Any) -> List[PIIFinding]:
        """Process document block-by-block and attach block_id to all findings."""
        blocks = getattr(document, "blocks", [])
        all_findings: List[PIIFinding] = []

        for block in blocks:
            text = getattr(block, "text", "") or ""
            if not text.strip():
                continue
            block_findings = self.detect(text)
            for f in block_findings:
                if getattr(f, "block_id", None) is None:
                    f.block_id = block.block_id
            all_findings.extend(block_findings)

        return all_findings

    def detect(self, text: Union[str, Any]) -> List[PIIFinding]:
        """Detect PII findings, applying context gates, checksums, and deconfliction."""
        if hasattr(text, "blocks"):
            return self.detect_document(text)

        if not isinstance(text, str):
            raise TypeError("text must be a string")

        # Prioritize phone number detection before any date extraction
        phone_findings = self._detect_phone_numbers(text)
        phone_spans = [(f.start, f.end) for f in phone_findings]

        results = self.analyzer.analyze(text=text, language="en")
        findings: List[PIIFinding] = list(phone_findings)

        for result in results:
            raw_type = result.entity_type
            start, end = result.start, result.end
            value = text[start:end]
            norm_val = value.strip().casefold()

            # Ignore contact labels falsely classified as person names
            if raw_type == "PERSON" and norm_val in {
                "mobile", "phone", "telephone", "email", "contact", "address"
            }:
                continue

            # Strict validation for PERSON
            if raw_type == "PERSON":
                if result.score < 0.85:
                    continue
                if not is_valid_person_name(value):
                    continue
                exp_start, exp_end, exp_val = expand_name_span(text, start, end)
                if not is_valid_person_name(exp_val):
                    continue
                start, end, value = exp_start, exp_end, exp_val
                norm_val = value.strip().casefold()

            # Clean trailing punctuation from EMAIL
            if raw_type == "EMAIL_ADDRESS":
                clean_email = value.rstrip(".,;:!?)]}>")
                end = start + len(clean_email)
                value = text[start:end]
                norm_val = value.strip().casefold()

            # Avoid duplicating phone findings and track spans
            if raw_type in ("PHONE_NUMBER", "PHONE"):
                if any(self._spans_overlap(start, end, p_start, p_end) for p_start, p_end in phone_spans):
                    continue
                phone_spans.append((start, end))

            # Suppress vague temporal expressions, date stopwords, and invalid 4-digit years
            if raw_type in ("DATE", "DATE_TIME", "TIME"):
                if any(self._spans_overlap(start, end, p_start, p_end) for p_start, p_end in phone_spans):
                    continue
                if self._is_date_stopword(value):
                    continue
                if self._is_vague_date_phrase(value):
                    continue
                if DIGIT_ONLY_CODE_PATTERN.fullmatch(value.strip()):
                    continue
                if not self._is_valid_four_digit_year(text, start, end, value):
                    continue

            if raw_type == "US_DRIVER_LICENSE":
                continue
            if raw_type == "LOCATION":
                continue

            entity_type = ENTITY_MAPPING.get(raw_type, raw_type)

            if raw_type in ("DATE", "DATE_TIME"):
                entity_type = self._classify_date(text, start)

            if entity_type == "AADHAAR" and not self._has_context(
                text, start, end, ("aadhaar", "uid", "unique identification number")
            ):
                continue

            if entity_type == "PASSPORT" and not self._has_context(
                text, start, end, ("passport", "passport number", "passport no")
            ):
                continue

            if entity_type == "ACCOUNT_NUMBER" and not self._has_context(
                text, start, end, ("account number", "account no", "bank account", "a/c number", "a/c no")
            ):
                continue

            if entity_type == "SSN":
                if not SSN_STRICT_PATTERN.fullmatch(value.strip()):
                    continue

            if entity_type == "CARD_NUMBER" and not self._passes_luhn(value):
                continue

            if raw_type == "PERSON":
                if not is_valid_person_name(value):
                    continue
                nearby = text[max(0, start - 20):min(len(text), end + 20)].casefold()
                if any(lbl in nearby for lbl in ("birth date", "date of birth", "date of joining", "joining date")):
                    continue

            # Allowlist lookup
            if is_allowlisted(entity_type, value):
                continue

            findings.append(
                PIIFinding(
                    entity_type=entity_type,
                    text=value,
                    start=start,
                    end=end,
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
            if any(self._spans_overlap(m_start, m_end, c_start, c_end) for c_start, c_end in card_spans):
                continue
            findings.append(
                PIIFinding(
                    entity_type="CARD_NUMBER",
                    text=candidate,
                    start=m_start,
                    end=m_end,
                    confidence=0.75,
                    detector="LuhnValidatedCardFallback",
                )
            )
            card_spans.append((m_start, m_end))

        # SSN Fallback
        for match in SSN_STRICT_PATTERN.finditer(text):
            start, end = match.span()
            if any(f.entity_type == "SSN" and self._spans_overlap(start, end, f.start, f.end) for f in findings):
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

        # Executive Roster Gazetteer Matching
        person_spans = [(f.start, f.end) for f in findings if f.entity_type == "PERSON_NAME"]
        for exec_name in EXECUTIVE_ROSTER:
            for m in re.finditer(rf"\b{re.escape(exec_name)}\b", text):
                m_start, m_end = m.span()
                matched_text = text[m_start:m_end]
                if is_allowlisted("PERSON_NAME", matched_text):
                    continue
                # Check if already covered
                if not any(f_start <= m_start and m_end <= f_end for f_start, f_end in person_spans):
                    findings.append(
                        PIIFinding(
                            entity_type="PERSON_NAME",
                            text=matched_text,
                            start=m_start,
                            end=m_end,
                            confidence=0.99,
                            detector="ExecutiveRosterGazetteer",
                        )
                    )
                    person_spans.append((m_start, m_end))

        # Role & Header Context Name Recognizer
        for match in _ROLE_LABEL_PATTERN.finditer(text):
            cand_name = match.group(1).strip().rstrip(".,;:")
            cand_start = match.start(1)
            cand_end = cand_start + len(cand_name)
            if is_valid_person_name(cand_name):
                exp_st, exp_en, exp_val = expand_name_span(text, cand_start, cand_end)
                if is_valid_person_name(exp_val):
                    if not any(f_start <= exp_st and exp_en <= f_end for f_start, f_end in person_spans):
                        findings.append(
                            PIIFinding(
                                entity_type="PERSON_NAME",
                                text=text[exp_st:exp_en],
                                start=exp_st,
                                end=exp_en,
                                confidence=0.95,
                                detector="RoleContextNameRecognizer",
                            )
                        )
                        person_spans.append((exp_st, exp_en))

        # Email Lenient Fallback (handles spaces before @)
        email_spans = [(f.start, f.end) for f in findings if f.entity_type == "EMAIL"]
        for match in _EMAIL_LENIENT_PATTERN.finditer(text):
            m_val = match.group(0).rstrip(".,;:!?)]}>")
            m_start = match.start()
            m_end = m_start + len(m_val)
            if is_allowlisted("EMAIL", m_val):
                continue
            if not any(self._spans_overlap(m_start, m_end, e_start, e_end) for e_start, e_end in email_spans):
                findings.append(
                    PIIFinding(
                        entity_type="EMAIL",
                        text=text[m_start:m_end],
                        start=m_start,
                        end=m_end,
                        confidence=0.95,
                        detector="LenientEmailRecognizer",
                    )
                )
                email_spans.append((m_start, m_end))

        # Conflict & Overlap Resolution:
        # Prioritize longer PERSON_NAME and PHONE spans over shorter sub-spans
        email_spans = [(f.start, f.end) for f in findings if f.entity_type == "EMAIL"]
        phone_spans = [(f.start, f.end) for f in findings if f.entity_type == "PHONE"]

        resolved_findings: List[PIIFinding] = []
        for item in findings:
            if item.entity_type == "PERSON_NAME" and not is_valid_person_name(item.text):
                continue
            if item.entity_type == "URL" and any(e_start <= item.start and item.end <= e_end for e_start, e_end in email_spans):
                continue
            if item.entity_type in ("DATE", "DATE_OF_BIRTH"):
                if any(self._spans_overlap(item.start, item.end, p_start, p_end) for p_start, p_end in phone_spans):
                    continue
                if self._is_date_stopword(item.text):
                    continue
                if not self._is_valid_four_digit_year(text, item.start, item.end, item.text):
                    continue
            resolved_findings.append(item)

        # Deconflict overlapping phone numbers: keep longer span
        phone_items = [f for f in resolved_findings if f.entity_type == "PHONE"]
        other_items = [f for f in resolved_findings if f.entity_type != "PHONE"]

        phone_items.sort(key=lambda f: (f.start, -(f.end - f.start)))
        filtered_phones: List[PIIFinding] = []
        last_phone_end = -1
        for p in phone_items:
            if p.start >= last_phone_end:
                filtered_phones.append(p)
                last_phone_end = p.end

        # Deconflict overlapping person names: keep longer span
        person_items = [f for f in other_items if f.entity_type == "PERSON_NAME"]
        non_person_items = [f for f in other_items if f.entity_type != "PERSON_NAME"]
        
        person_items.sort(key=lambda f: (f.start, -(f.end - f.start)))
        filtered_persons: List[PIIFinding] = []
        last_end = -1
        for p in person_items:
            if p.start >= last_end:
                filtered_persons.append(p)
                last_end = p.end

        final_findings = non_person_items + filtered_phones + filtered_persons
        unique_findings: List[PIIFinding] = []
        seen = set()
        for item in final_findings:
            key = (item.entity_type, item.start, item.end)
            if key not in seen:
                seen.add(key)
                unique_findings.append(item)

        unique_findings.sort(key=lambda item: (item.start, item.end))
        return unique_findings


def detect_pii_in_document(document: Document) -> List[PIIFinding]:
    """Module-level helper matching the pipeline entrypoint contract."""
    detector = PIIDetector()
    return detector.detect_document(document)