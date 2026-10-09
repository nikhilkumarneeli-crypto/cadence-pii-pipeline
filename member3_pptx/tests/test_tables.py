"""Table Extraction Tests for Member 3 PPTX Engine.
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


def test_table_extraction_counts(extractor: PPTXExtractor, pptx_dir: Path):
    """Verify table and table cell block counts in test2."""
    p_path = pptx_dir / "test2_tables_pii.pptx"
    result = extractor.extract(p_path)

    # 2 table parent blocks
    tables = [b for b in result.blocks if b.block_type == "table"]
    assert len(tables) == 2

    # Verify table cells
    cells = [b for b in result.blocks if b.block_type == "table_cell"]
    assert len(cells) == 32  # 20 cells in table 1, 12 cells in table 2


def test_table_cell_metadata(extractor: PPTXExtractor, pptx_dir: Path):
    """Verify row, column, header flag, and bounding box coordinates for cells."""
    p_path = pptx_dir / "test2_tables_pii.pptx"
    result = extractor.extract(p_path)

    cells = [b for b in result.blocks if b.block_type == "table_cell"]
    for c in cells:
        assert c.table_metadata is not None
        assert "row" in c.table_metadata
        assert "column" in c.table_metadata
        assert "is_header" in c.table_metadata
        # Coordinates must be valid non-negative floats
        assert c.position.left >= 0.0
        assert c.position.top >= 0.0
        assert c.position.width > 0.0
        assert c.position.height > 0.0


def test_table_content_fidelity(extractor: PPTXExtractor, pptx_dir: Path):
    """Verify exact synthetic PII preservation inside table cells."""
    p_path = pptx_dir / "test2_tables_pii.pptx"
    result = extractor.extract(p_path)

    cell_texts = {b.text for b in result.blocks if b.block_type == "table_cell"}
    assert "Arthur Pendelton" in cell_texts
    assert "a.pendelton@fintechvendor.example" in cell_texts
    assert "+1 (555) 789-0123" in cell_texts
    assert "Ethan Gallagher" in cell_texts
    assert "e.gallagher@cadencefg.example" in cell_texts
    assert "Fatima Al-Mansoor" in cell_texts


def test_complex_tables_in_cadence_org_pack(extractor: PPTXExtractor, pptx_dir: Path):
    """Verify extraction of large RACI matrices and Role Holder directory tables."""
    pack_path = pptx_dir / "Cadence_Financial_Group_Organizational_Pack.pptx"
    result = extractor.extract(pack_path)

    tables = [b for b in result.blocks if b.block_type == "table"]
    assert len(tables) == 3  # RACI 1 (slide 6), RACI 2 (slide 7), Directory (slide 8)

    cells = [b for b in result.blocks if b.block_type == "table_cell"]
    assert len(cells) == 224

    directory_cells = [b for b in cells if b.slide == 8]
    assert len(directory_cells) > 50
    dir_texts = " ".join(b.text for b in directory_cells)
    assert "Solveig Aarnio" in dir_texts
    assert "s.aarnio@cadencefg.example" in dir_texts
