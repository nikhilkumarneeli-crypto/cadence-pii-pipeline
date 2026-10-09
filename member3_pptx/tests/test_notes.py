"""Speaker Notes Extraction Tests for Member 3 PPTX Engine.
Cadence Financial Group - Case Study 2: Text Analysis & PII Detection.
"""

from pathlib import Path
import pytest
from src.pptx_extractor.extractor import PPTXExtractor


@pytest.fixture
def pptx_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "test_data" / "pptx"


@pytest.fixture
def extractor() -> PPTXExtractor:
    return PPTXExtractor()


def test_speaker_notes_extraction(extractor: PPTXExtractor, pptx_dir: Path):
    """Verify notes extraction, slide association, and block type in test6."""
    p_path = pptx_dir / "test6_speaker_notes_pii.pptx"
    result = extractor.extract(p_path)

    notes = [b for b in result.blocks if b.block_type == "speaker_notes"]
    assert len(notes) == 2

    # Slide 1 notes
    n1 = [n for n in notes if n.slide == 1][0]
    assert "Marcus Brody" in n1.text
    assert "m.brody@cadencefg.example" in n1.text
    assert "+1 (555) 432-1098" in n1.text
    assert n1.source_type == "speaker_notes"

    # Slide 2 notes
    n2 = [n for n in notes if n.slide == 2][0]
    assert "Nina Rostova" in n2.text
    assert "n.rostova@cadencefg.example" in n2.text
    assert "+1 (555) 432-1099" in n2.text


def test_notes_isolated_from_slide_body(extractor: PPTXExtractor, pptx_dir: Path):
    """Ensure speaker notes are never mixed into normal slide body text boxes."""
    p_path = pptx_dir / "test6_speaker_notes_pii.pptx"
    result = extractor.extract(p_path)

    body_blocks = [b for b in result.blocks if b.block_type != "speaker_notes"]
    for b in body_blocks:
        assert "Marcus Brody" not in b.text
        assert "Nina Rostova" not in b.text


def test_slides_without_notes_have_no_notes_blocks(extractor: PPTXExtractor, pptx_dir: Path):
    """Ensure decks with no speaker notes produce 0 speaker_notes blocks."""
    p_path = pptx_dir / "test1_text_boxes_pii.pptx"
    result = extractor.extract(p_path)

    notes = [b for b in result.blocks if b.block_type == "speaker_notes"]
    assert len(notes) == 0
