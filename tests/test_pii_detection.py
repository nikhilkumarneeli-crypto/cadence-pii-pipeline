import pytest

from src.detection.engine import PIIDetector
from src.detection.allowlist import ALLOWLIST


@pytest.fixture(scope="module")
def detector():
    """Instantiate a single detector instance for the entire test session."""
    return PIIDetector()


def get_findings(detector, text):
    """Return findings as a set of (entity_type, text) pairs."""
    return {
        (finding.entity_type, finding.text)
        for finding in detector.detect(text)
    }


def assert_span_offsets_are_exact(detector, text):
    """Verify character slices in original text strictly equal the finding's text."""
    findings = detector.detect(text)
    for finding in findings:
        assert text[finding.start:finding.end] == finding.text, (
            f"Offset mismatch for {finding.entity_type}: "
            f"expected '{finding.text}', got '{text[finding.start:finding.end]}'"
        )


# =====================================================================
# Core Recognition Tests
# =====================================================================

def test_detect_indian_pii(detector):
    text = (
        "Name: Priyanka Raghavan; "
        "email: priya@example.com; "
        "Employee ID: EMP-40318; "
        "DOB: 07/03/2006; "
        "PAN: ABCDE1234F; "
        "Aadhaar: 2345 6789 0123; "
        "Phone: +91 98765 43210; "
        "Passport number: K1234567; "
        "Account number: 123456789012"
    )

    findings = get_findings(detector, text)

    expected = {
        ("PERSON_NAME", "Priyanka Raghavan"),
        ("EMAIL", "priya@example.com"),
        ("EMPLOYEE_ID", "EMP-40318"),
        ("DATE_OF_BIRTH", "07/03/2006"),
        ("PAN", "ABCDE1234F"),
        ("AADHAAR", "2345 6789 0123"),
        ("PHONE", "+91 98765 43210"),
        ("PASSPORT", "K1234567"),
        ("ACCOUNT_NUMBER", "123456789012"),
    }

    assert findings == expected
    assert_span_offsets_are_exact(detector, text)


def test_email_is_detected(detector):
    text = "Contact: priya@example.com"
    findings = get_findings(detector, text)

    assert findings == {("EMAIL", "priya@example.com")}
    assert_span_offsets_are_exact(detector, text)


def test_allowlisted_email_is_filtered(detector, monkeypatch):
    monkeypatch.setitem(
        ALLOWLIST,
        "EMAIL",
        {"priya@example.com"},
    )

    findings = get_findings(detector, "Contact: priya@example.com")
    assert ("EMAIL", "priya@example.com") not in findings


# =====================================================================
# Card Number & Checksum Tests
# =====================================================================

def test_credit_card_number_is_detected(detector):
    text = "Test card number: 4111111111111111"
    findings = get_findings(detector, text)

    assert ("CARD_NUMBER", "4111111111111111") in findings
    assert_span_offsets_are_exact(detector, text)


def test_invalid_credit_card_checksum_is_rejected(detector):
    findings = get_findings(detector, "Test card number: 4111111111111112")
    assert not any(entity == "CARD_NUMBER" for entity, _ in findings)


def test_luhn_valid_card_without_card_label_is_detected(detector):
    text = "Help me with booking an executive flight using my 2681141721246076."
    findings = get_findings(detector, text)

    assert ("CARD_NUMBER", "2681141721246076") in findings
    assert_span_offsets_are_exact(detector, text)


@pytest.mark.parametrize(
    "formatted_card",
    [
        "4111 1111 1111 1111",
        "4111-1111-1111-1111",
    ],
)
def test_formatted_credit_card_variants_detected(detector, formatted_card):
    text = f"Payment details: {formatted_card}"
    findings = get_findings(detector, text)

    assert ("CARD_NUMBER", formatted_card) in findings
    assert_span_offsets_are_exact(detector, text)


def test_benchmark_invalid_luhn_card_rejected(detector):
    # Benchmark number known to fail Luhn validation
    text = "Account reference 676305360015 provided."
    findings = get_findings(detector, text)

    assert ("CARD_NUMBER", "676305360015") not in findings


# =====================================================================
# SSN Detection & Formatting Tests
# =====================================================================

def test_ssn_is_detected_with_context(detector):
    text = "SSN: 123-45-6789"
    findings = get_findings(detector, text)

    assert ("SSN", "123-45-6789") in findings
    assert_span_offsets_are_exact(detector, text)


def test_unlabelled_formatted_ssn_is_detected(detector):
    text = "The document contains sensitive information such as 389-41-4302."
    findings = get_findings(detector, text)

    assert ("SSN", "389-41-4302") in findings
    assert_span_offsets_are_exact(detector, text)


@pytest.mark.parametrize(
    "invalid_ssn",
    [
        "123-45-678",    # Missing digit
        "123-456-7890",  # Invalid grouping
        "123456789",     # No delimiters (fallback requires strict formatting)
    ],
)
def test_malformed_ssn_not_detected_as_ssn(detector, invalid_ssn):
    text = f"ID: {invalid_ssn}"
    findings = get_findings(detector, text)

    assert ("SSN", invalid_ssn) not in findings


# =====================================================================
# Address Tests
# =====================================================================

def test_labelled_home_address_is_one_finding(detector):
    text = (
        "Home address: 24 MG Road, Bengaluru, Karnataka 560001. "
        "The meeting is in Bengaluru."
    )

    findings = get_findings(detector, text)

    expected = (
        "HOME_ADDRESS",
        "24 MG Road, Bengaluru, Karnataka 560001",
    )

    assert expected in findings
    assert ("HOME_ADDRESS", "Bengaluru") not in findings
    assert ("HOME_ADDRESS", "Karnataka") not in findings
    assert_span_offsets_are_exact(detector, text)


def test_ordinary_city_is_not_home_address(detector):
    findings = get_findings(detector, "The meeting is in Bengaluru.")
    assert not any(entity == "HOME_ADDRESS" for entity, _ in findings)


# =====================================================================
# Date / Time Edge Cases & Disambiguation
# =====================================================================

def test_phone_number_is_not_detected_as_date(detector):
    text = "Phone: +91 98765 43210"
    findings = get_findings(detector, text)

    assert ("PHONE", "+91 98765 43210") in findings
    assert not any(entity in {"DATE", "DATE_OF_BIRTH"} for entity, _ in findings)
    assert_span_offsets_are_exact(detector, text)


def test_numeric_codes_are_not_detected_as_dates(detector):
    text = "The report contains 12345 items and an invoice total of 25000."
    findings = get_findings(detector, text)

    assert not any(entity in {"DATE", "DATE_OF_BIRTH", "TIME"} for entity, _ in findings)


def test_meeting_date_is_not_classified_as_dob(detector):
    text = "The meeting date is 15/09/2026."
    findings = get_findings(detector, text)

    assert ("DATE", "15/09/2026") in findings
    assert ("DATE_OF_BIRTH", "15/09/2026") not in findings
    assert_span_offsets_are_exact(detector, text)


def test_actual_calendar_date_is_still_detected(detector):
    text = "The meeting is scheduled for 15/09/2026."
    findings = get_findings(detector, text)

    assert ("DATE", "15/09/2026") in findings
    assert_span_offsets_are_exact(detector, text)


@pytest.mark.parametrize(
    "phrase",
    [
        "hours",
        "the day",
        "the past year",
        "over a month",
        "quarterly",
        "in 3 days",
        "for a few hours",
        "throughout the day",
    ],
)
def test_vague_date_phrases_are_not_detected_as_dates(detector, phrase):
    text = f"The report discusses {phrase} in detail."
    findings = get_findings(detector, text)

    # Asserts that no false date or time entity was captured for the vague phrase
    assert not any(
        entity in {"DATE", "DATE_OF_BIRTH", "DATE_TIME", "TIME"}
        for entity, _ in findings
    )


# =====================================================================
# Boundary, Overlap & Input Validation Tests
# =====================================================================

def test_non_string_input_raises_error(detector):
    with pytest.raises(TypeError):
        detector.detect(None)


@pytest.mark.parametrize("blank_input", ["", "   ", "\n\t"])
def test_empty_or_whitespace_input_returns_empty_list(detector, blank_input):
    assert detector.detect(blank_input) == []


def test_url_inside_email_is_suppressed(detector):
    text = "Please reach out to support@acme-corp.com today."
    findings = get_findings(detector, text)

    assert ("EMAIL", "support@acme-corp.com") in findings
    assert ("URL", "acme-corp.com") not in findings
    assert_span_offsets_are_exact(detector, text)


def test_finding_order_is_strictly_chronological(detector):
    text = "Name: John Doe, Email: john@example.com, SSN: 123-45-6789"
    results = detector.detect(text)

    starts = [item.start for item in results]
    assert starts == sorted(starts), "Findings must be returned in natural document order."