"""Tests ensuring business terminology and TPRM vocabulary are not misclassified as PERSON entities."""
import pytest
from src.detection.allowlist import FORBIDDEN_NAME_WORDS, is_forbidden_name
from src.detection.engine import PIIDetector, is_valid_person_name, is_governance_term


def test_forbidden_words_populated():
    for word in [
        "diligence", "due", "partner", "partners", "vendor", "vendors",
        "group", "groups", "team", "teams", "tier", "category",
        "classification", "confidential", "internal", "external",
        "provider", "providers", "service", "services", "management",
        "governance", "compliance", "workflow", "workflows", "template",
        "templates", "questionnaire", "questionnaires", "assessment",
        "assessments", "training", "risk", "risks", "security", "quality",
        "owner", "owners", "reviewer", "reviewers", "lead", "leads",
        "contact", "contacts", "audit", "process", "processes",
        "integration", "requirement", "requirements", "rule", "rules",
        "stage", "stages", "attribute", "attributes",
    ]:
        assert word in FORBIDDEN_NAME_WORDS


@pytest.mark.parametrize("phrase", [
    "Due Diligence",
    "Revenue Partners",
    "Marketing Partners",
    "International Vendors",
    "Staffing Vendors",
    "Vendor Tier",
    "Vendor Category",
    "Business Owner",
    "Data Quality",
    "Client Confidential",
    "User Groups",
    "Legal Group",
    "Finance Group",
    "Procurement Group",
    "IT Group",
    "Privacy Group",
    "Security Group",
    "Data Quality Group",
    "Offboarding Workflow",
    "Onboarding Workflow",
    "Send RevPart Questionnaire",
    "Due Diligence Questionnaire",
    "Final Due Diligence Questionnaire",
    "Assessment Completion",
    "Assessment Submitted",
    "Legal Risk Identified",
    "Procurement Risk Identified",
    "Finance Risk Identified",
    "Privacy Risk Identified",
    "Security Risk Identified",
    "IT Risk Identified",
    "IT Requirement Identified",
    "Data Classification",
    "Client Contact",
    "QA Reviewer",
    "Peer Reviewer",
    "STAGE RULE",
    "WORKFLOW RULE",
    "No Stage Rule",
    "No Workflow Rule",
])
def test_business_terms_not_valid_person(phrase: str):
    assert is_forbidden_name(phrase) is True
    assert is_valid_person_name(phrase) is False


@pytest.mark.parametrize("phrase", [
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
    "Miriam T. Achebe",
    "Anthony P. Brightwell",
    "Delphine R. Okonjo",
    "Beatrix S. Lindenau",
    "Eleanor R. Vasquez-Holt",
    "Mireille Dubois-Kane",
])
def test_real_names_are_valid(phrase: str):
    assert is_valid_person_name(phrase) is True


def test_detector_filters_business_terms_in_text():
    detector = PIIDetector()
    text = (
        "During Due Diligence, Revenue Partners and Marketing Partners review the "
        "Vendor Tier and Vendor Category with the Business Owner. Data Quality and "
        "Client Confidential status are managed by User Groups and the Legal Group."
    )
    findings = detector.detect(text)
    person_findings = [f for f in findings if f.entity_type == "PERSON_NAME"]
    assert len(person_findings) == 0


def test_detector_captures_real_names_in_text():
    detector = PIIDetector()
    text = (
        "The policy was authored by Daniela Figueroa and reviewed by Chris Schmitz "
        "and Siddharth Gaikwad."
    )
    findings = detector.detect(text)
    person_texts = [f.text for f in findings if f.entity_type == "PERSON_NAME"]
    assert "Daniela Figueroa" in person_texts
    assert "Chris Schmitz" in person_texts
    assert "Siddharth Gaikwad" in person_texts
