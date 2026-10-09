"""Structure-Retention Metric Tests for Member 3 PPTX Engine.
Cadence Financial Group - Case Study 2: Text Analysis & PII Detection.
"""

from pathlib import Path
import pytest
from src.pptx_extractor.extractor import PPTXExtractor
from src.pptx_extractor.structure_metric import StructureMetricEngine


@pytest.fixture
def pptx_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "test_data" / "pptx"


@pytest.fixture
def extractor() -> PPTXExtractor:
    return PPTXExtractor()


@pytest.fixture
def metric_engine() -> StructureMetricEngine:
    return StructureMetricEngine(target_percent=80.0)


def test_target_threshold_is_80_percent(metric_engine: StructureMetricEngine):
    """Verify target threshold default is 80.0% as required by case study."""
    assert metric_engine.target_percent == 80.0


def test_evaluation_test1_passes_target(extractor: PPTXExtractor, metric_engine: StructureMetricEngine, pptx_dir: Path):
    """Verify test1 achieves >= 80% and status PASS."""
    p_path = pptx_dir / "test1_text_boxes_pii.pptx"
    result = extractor.extract(p_path)
    eval_res = metric_engine.evaluate(p_path, result)

    assert eval_res.passed is True
    assert eval_res.status == "PASS"
    assert eval_res.overall_score_percent >= 80.0
    assert eval_res.total_slides == 2


def test_evaluation_test2_tables_passes_target(extractor: PPTXExtractor, metric_engine: StructureMetricEngine, pptx_dir: Path):
    """Verify test2 achieves >= 80% with high table and cell preservation."""
    p_path = pptx_dir / "test2_tables_pii.pptx"
    result = extractor.extract(p_path)
    eval_res = metric_engine.evaluate(p_path, result)

    assert eval_res.passed is True
    assert eval_res.status == "PASS"
    assert eval_res.overall_score_percent >= 80.0

    table_comp = eval_res.component_scores.get("table_preservation")
    cell_comp = eval_res.component_scores.get("table_cell_preservation")
    assert table_comp is not None and table_comp.raw_ratio == 1.0
    assert cell_comp is not None and cell_comp.raw_ratio == 1.0


def test_evaluation_cadence_org_pack_passes_target(extractor: PPTXExtractor, metric_engine: StructureMetricEngine, pptx_dir: Path):
    """Verify Cadence Organizational Pack achieves >= 80% structure retention."""
    pack_path = pptx_dir / "Cadence_Financial_Group_Organizational_Pack.pptx"
    result = extractor.extract(pack_path)
    eval_res = metric_engine.evaluate(pack_path, result)

    assert eval_res.passed is True
    assert eval_res.status == "PASS"
    assert eval_res.overall_score_percent >= 80.0
    assert eval_res.total_slides == 9


def test_weights_sum_to_one(metric_engine: StructureMetricEngine):
    """Verify all configurable structural weights sum to 1.0."""
    total_w = sum(metric_engine.weights.values())
    assert abs(total_w - 1.0) < 1e-4
