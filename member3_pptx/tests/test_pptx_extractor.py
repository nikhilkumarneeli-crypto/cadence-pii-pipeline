"""Unit and Integration Tests for PPTX Extractor Engine.
Cadence Financial Group - Case Study 2: Text Analysis & PII Detection.
Member 3.
"""

from pathlib import Path
import pytest
from src.pptx_extractor.extractor import PPTXExtractor
from src.pptx_extractor.schema import ExtractedBlock, PPTXExtractionResult, Position


@pytest.fixture
def pptx_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "test_data" / "pptx"


@pytest.fixture
def extractor() -> PPTXExtractor:
    return PPTXExtractor()


def test_extractor_initialization(extractor: PPTXExtractor):
    """Test extractor initialization and component readiness."""
    assert extractor is not None
    assert extractor.ordering_engine is not None
    assert extractor.context_grouping_engine is not None


def test_missing_file_raises_not_found(extractor: PPTXExtractor):
    """Test handling of nonexistent PPTX path."""
    with pytest.raises(FileNotFoundError):
        extractor.extract("non_existent_presentation_file.pptx")


def test_extract_test1_text_boxes(extractor: PPTXExtractor, pptx_dir: Path):
    """Verify extraction of text boxes, titles, and paragraphs in test1."""
    p_path = pptx_dir / "test1_text_boxes_pii.pptx"
    result = extractor.extract(p_path)

    assert result.file_name == "test1_text_boxes_pii.pptx"
    assert result.total_slides == 2
    assert result.extracted_slides == 2
    assert result.total_blocks >= 4

    # Verify PII texts are present in extracted blocks
    all_text = " ".join(b.text for b in result.blocks)
    assert "Eleanor Vance" in all_text
    assert "e.vance@cadencefg.example" in all_text
    assert "+1 (555) 234-8901" in all_text
    assert "CFG-EXEC-0101" in all_text
    assert "Julian Thorne" in all_text
    assert "Siddharth Rao" in all_text
    assert "Claire Dupont" in all_text


def test_schema_compliance(extractor: PPTXExtractor, pptx_dir: Path):
    """Validate that every extracted block adheres to the common JSON schema."""
    p_path = pptx_dir / "test1_text_boxes_pii.pptx"
    result = extractor.extract(p_path)

    for block in result.blocks:
        d = block.to_dict()
        # Verify required keys from team schema
        assert "file" in d and isinstance(d["file"], str)
        assert "slide" in d and isinstance(d["slide"], int)
        assert "section" in d
        assert "block_id" in d and isinstance(d["block_id"], str)
        assert "block_type" in d and isinstance(d["block_type"], str)
        assert "text" in d and isinstance(d["text"], str)
        assert "position" in d and isinstance(d["position"], dict)
        assert "left" in d["position"]
        assert "top" in d["position"]
        assert "width" in d["position"]
        assert "height" in d["position"]
        assert "order" in d and isinstance(d["order"], int)
        assert "context_group_id" in d and isinstance(d["context_group_id"], str)
        assert "source_type" in d and isinstance(d["source_type"], str)


def test_extract_cadence_organizational_pack(extractor: PPTXExtractor, pptx_dir: Path):
    """Verify end-to-end extraction on the supplied Cadence Organizational Reference Pack."""
    pack_path = pptx_dir / "Cadence_Financial_Group_Organizational_Pack.pptx"
    if not pack_path.exists():
        pytest.skip("Cadence Organizational Pack not present in test_data/pptx")

    result = extractor.extract(pack_path)
    assert result.total_slides == 9
    assert result.extracted_slides == 9
    assert result.total_blocks > 100

    all_text = " ".join(b.text for b in result.blocks)
    assert "Marguerite Vossberg" in all_text
    assert "m.vossberg@cadencefg.example" in all_text
    assert "Desmond Achterberg" in all_text
    assert "Tobias Lindqvist" in all_text
    assert "Adaeze Okonkwo-Bell" in all_text
    assert "RACI" in all_text


def test_json_save_and_load(extractor: PPTXExtractor, pptx_dir: Path, tmp_path: Path):
    """Test saving and re-loading extraction results as JSON."""
    p_path = pptx_dir / "test1_text_boxes_pii.pptx"
    result = extractor.extract(p_path)

    out_file = tmp_path / "test1_output.json"
    result.save_json(out_file)
    assert out_file.exists()

    loaded = PPTXExtractionResult.load_json(out_file)
    assert loaded.file_name == result.file_name
    assert loaded.total_slides == result.total_slides
    assert len(loaded.blocks) == len(result.blocks)
