"""Deterministic Reading Order Tests for Member 3 PPTX Engine.
Cadence Financial Group - Case Study 2: Text Analysis & PII Detection.
"""

from pathlib import Path
import pytest
from src.pptx_extractor.extractor import PPTXExtractor
from src.pptx_extractor.ordering import DeterministicOrderingEngine
from src.pptx_extractor.schema import ExtractedBlock, Position


@pytest.fixture
def pptx_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "test_data" / "pptx"


@pytest.fixture
def extractor() -> PPTXExtractor:
    return PPTXExtractor()


def test_monotonic_order_sequence(extractor: PPTXExtractor, pptx_dir: Path):
    """Verify that assigned order numbers are strictly monotonic: 1, 2, 3..."""
    p_path = pptx_dir / "test7_mixed_complex_pii.pptx"
    result = extractor.extract(p_path)

    orders = [b.order for b in result.blocks]
    assert orders == list(range(1, len(result.blocks) + 1))


def test_title_priority_over_body():
    """Verify title shape appears before body shapes located below it."""
    engine = DeterministicOrderingEngine()
    blocks = [
        ExtractedBlock(
            file="mock.pptx", slide=1, section=None, block_id="b2",
            block_type="text_box", text="Body text",
            position=Position(left=100.0, top=150.0, width=400.0, height=200.0),
            order=2, context_group_id="g1", source_type="text_box"
        ),
        ExtractedBlock(
            file="mock.pptx", slide=1, section=None, block_id="b1",
            block_type="title", text="Header Title",
            position=Position(left=100.0, top=40.0, width=400.0, height=60.0),
            order=1, context_group_id="g1", source_type="text_box"
        ),
    ]

    ordered = engine.order_blocks(blocks)
    assert ordered[0].block_type == "title"
    assert ordered[0].text == "Header Title"
    assert ordered[1].text == "Body text"


def test_speaker_notes_placed_last():
    """Verify speaker notes always follow slide body blocks."""
    engine = DeterministicOrderingEngine()
    blocks = [
        ExtractedBlock(
            file="mock.pptx", slide=1, section=None, block_id="n1",
            block_type="speaker_notes", text="Notes content",
            position=Position(left=0.0, top=1000.0, width=600.0, height=100.0),
            order=1, context_group_id="notes", source_type="speaker_notes"
        ),
        ExtractedBlock(
            file="mock.pptx", slide=1, section=None, block_id="t1",
            block_type="title", text="Slide Title",
            position=Position(left=50.0, top=30.0, width=400.0, height=50.0),
            order=2, context_group_id="g1", source_type="text_box"
        ),
        ExtractedBlock(
            file="mock.pptx", slide=1, section=None, block_id="b1",
            block_type="text_box", text="Slide Body",
            position=Position(left=50.0, top=100.0, width=400.0, height=150.0),
            order=3, context_group_id="g1", source_type="text_box"
        ),
    ]

    ordered = engine.order_blocks(blocks)
    assert ordered[0].block_type == "title"
    assert ordered[1].block_type == "text_box"
    assert ordered[2].block_type == "speaker_notes"
