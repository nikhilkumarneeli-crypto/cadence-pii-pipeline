"""Grouped Shapes Extraction Tests for Member 3 PPTX Engine.
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


def test_grouped_shapes_traversal(extractor: PPTXExtractor, pptx_dir: Path):
    """Verify recursive extraction of grouped shapes in test3."""
    p_path = pptx_dir / "test3_grouped_shapes_pii.pptx"
    result = extractor.extract(p_path)

    assert result.total_slides == 2
    # Total blocks: 2 titles + 3 grouped shapes in slide 1 + 3 in slide 2 = 8
    assert len(result.blocks) == 8

    # Check child shapes inside groups
    grouped_blocks = [b for b in result.blocks if b.source_type == "grouped_shape"]
    assert len(grouped_blocks) >= 6

    # Verify parent group IDs and group depth
    for gb in grouped_blocks:
        assert gb.parent_group_id is not None
        assert gb.group_depth >= 1


def test_nested_groups_recursion(extractor: PPTXExtractor, pptx_dir: Path):
    """Verify handling of nested group hierarchy on slide 2 of test3."""
    p_path = pptx_dir / "test3_grouped_shapes_pii.pptx"
    result = extractor.extract(p_path)

    slide2_blocks = [b for b in result.blocks if b.slide == 2 and b.source_type == "grouped_shape"]
    assert len(slide2_blocks) == 3

    # Check depths: top shape has depth 1, nested inner shapes have depth 2
    depths = {b.group_depth for b in slide2_blocks}
    assert 1 in depths
    assert 2 in depths

    # Verify PII preserved across nested groups
    texts = " ".join(b.text for b in slide2_blocks)
    assert "Ian MacIntyre" in texts
    assert "i.macintyre@cadencefg.example" in texts
    assert "Julia Chen" in texts
    assert "j.chen@cadencefg.example" in texts
    assert "+1 (555) 890-4321" in texts
