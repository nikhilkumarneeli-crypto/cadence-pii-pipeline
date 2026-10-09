"""Automated integration tests for Member 3 within the cadence-pii-pipeline project.

Validates:
- PPTX extraction conforming to src.common.schema (Document, TextBlock)
- Routing via src.router.route_and_extract()
- Pipeline processing via src.pipeline.PIIPipeline()
- Tables, cells, recursive group shapes, speaker notes, and 2D reading order
- Structure-retention metric evaluation exceeding the >= 80% target
"""

from pathlib import Path
import unittest

from src.common.schema import Document, TextBlock, PipelineResult
from src.extractors.pptx_extractor import PPTXExtractor, extract_pptx
from src.router import DocumentRouter, detect_file_type, route_and_extract
from src.pipeline import PIIPipeline
from src.evaluation.structure_metric import StructureMetricEngine, evaluate_structure_retention


class TestMember3PPTXExtractor(unittest.TestCase):
    """Tests for Member 3 PPTX extractor and schema integration."""

    @classmethod
    def setUpClass(cls):
        cls.data_dir = Path(__file__).resolve().parent / "data" / "member3_pptx"

    def test_missing_file_raises_not_found(self):
        with self.assertRaises(FileNotFoundError):
            extract_pptx(self.data_dir / "does_not_exist.pptx")

    def test_extract_pptx_returns_document(self):
        p_path = self.data_dir / "test1_text_boxes_pii.pptx"
        doc = extract_pptx(p_path)

        self.assertIsInstance(doc, Document)
        self.assertEqual(doc.file_type, "pptx")
        self.assertEqual(doc.filename, "test1_text_boxes_pii.pptx")
        self.assertGreaterEqual(len(doc.blocks), 4)

        # Check TextBlock properties
        first_b = doc.blocks[0]
        self.assertIsInstance(first_b, TextBlock)
        self.assertIsNotNone(first_b.block_id)
        self.assertIsNotNone(first_b.text)
        self.assertEqual(first_b.page_number, 1)
        self.assertIn("block_type", first_b.metadata)
        self.assertIn("position", first_b.metadata)

    def test_text_boxes_and_pii_preservation(self):
        p_path = self.data_dir / "test1_text_boxes_pii.pptx"
        doc = extract_pptx(p_path)
        all_text = doc.full_text

        self.assertIn("Eleanor Vance", all_text)
        self.assertIn("e.vance@cadencefg.example", all_text)
        self.assertIn("+1 (555) 234-8901", all_text)
        self.assertIn("CFG-EXEC-0101", all_text)
        self.assertIn("Julian Thorne", all_text)
        self.assertIn("Siddharth Rao", all_text)
        self.assertIn("Claire Dupont", all_text)

    def test_table_cell_grid_extraction(self):
        p_path = self.data_dir / "test2_tables_pii.pptx"
        doc = extract_pptx(p_path)

        cell_blocks = [b for b in doc.blocks if b.metadata.get("block_type") == "table_cell"]
        self.assertEqual(len(cell_blocks), 32)

        # Verify cell metadata
        for cell in cell_blocks:
            meta = cell.metadata
            self.assertIn("row", meta)
            self.assertIn("column", meta)
            self.assertIn("is_header", meta)
            self.assertIn("position", meta)
            self.assertIn("context_group_id", meta)

        # Verify cell PII content
        cell_texts = {b.text for b in cell_blocks}
        self.assertIn("Arthur Pendelton", cell_texts)
        self.assertIn("a.pendelton@fintechvendor.example", cell_texts)
        self.assertIn("+1 (555) 789-0123", cell_texts)
        self.assertIn("Ethan Gallagher", cell_texts)

    def test_recursive_grouped_shapes(self):
        p_path = self.data_dir / "test3_grouped_shapes_pii.pptx"
        doc = extract_pptx(p_path)

        grouped_blocks = [b for b in doc.blocks if b.metadata.get("source_type") == "grouped_shape"]
        self.assertGreaterEqual(len(grouped_blocks), 6)

        # Verify recursion depth and parent group tracking
        depths = {b.metadata.get("group_depth", 0) for b in grouped_blocks}
        self.assertTrue(any(d >= 1 for d in depths))

        texts = doc.full_text
        self.assertIn("Hannah Abbasi", texts)
        self.assertIn("Ian MacIntyre", texts)
        self.assertIn("Julia Chen", texts)

    def test_speaker_notes_isolation(self):
        p_path = self.data_dir / "test6_speaker_notes_pii.pptx"
        doc = extract_pptx(p_path)

        notes_blocks = [b for b in doc.blocks if b.metadata.get("block_type") == "speaker_notes"]
        self.assertEqual(len(notes_blocks), 2)

        # Check slide numbers and PII in notes
        self.assertEqual(notes_blocks[0].page_number, 1)
        self.assertIn("Marcus Brody", notes_blocks[0].text)
        self.assertEqual(notes_blocks[1].page_number, 2)
        self.assertIn("Nina Rostova", notes_blocks[1].text)


class TestRouterMember3Integration(unittest.TestCase):
    """Tests verifying DocumentRouter integrates with Member 3 PPTX extractor."""

    @classmethod
    def setUpClass(cls):
        cls.data_dir = Path(__file__).resolve().parent / "data" / "member3_pptx"

    def test_detect_file_type_pptx(self):
        self.assertEqual(detect_file_type("presentation.pptx"), "pptx")
        self.assertEqual(detect_file_type("PRESENTATION.PPTX"), "pptx")

    def test_route_and_extract_pptx(self):
        p_path = self.data_dir / "test1_text_boxes_pii.pptx"
        doc = route_and_extract(p_path)

        self.assertIsInstance(doc, Document)
        self.assertEqual(doc.file_type, "pptx")
        self.assertGreaterEqual(len(doc.blocks), 4)


class TestPipelineMember3Integration(unittest.TestCase):
    """Tests verifying end-to-end PIIPipeline with PPTX documents."""

    @classmethod
    def setUpClass(cls):
        cls.data_dir = Path(__file__).resolve().parent / "data" / "member3_pptx"

    def test_pipeline_pptx_extraction(self):
        p_path = self.data_dir / "test7_mixed_complex_pii.pptx"
        pipeline = PIIPipeline()
        result = pipeline.process(p_path)

        self.assertIsInstance(result, PipelineResult)
        self.assertEqual(result.document.file_type, "pptx")
        self.assertGreaterEqual(len(result.document.blocks), 10)
        self.assertIn("extraction", result.metadata["stages_executed"])


class TestStructureMetricMember3(unittest.TestCase):
    """Tests for Member 3 Structure-Retention Metric Engine."""

    @classmethod
    def setUpClass(cls):
        cls.data_dir = Path(__file__).resolve().parent / "data" / "member3_pptx"

    def test_structure_retention_target_threshold(self):
        engine = StructureMetricEngine(target_percent=80.0)
        self.assertEqual(engine.target_percent, 80.0)

    def test_structure_metric_exceeds_80_percent(self):
        p_path = self.data_dir / "test1_text_boxes_pii.pptx"
        doc = extract_pptx(p_path)
        eval_result = evaluate_structure_retention(p_path, doc, target_percent=80.0)

        self.assertTrue(eval_result["passed"])
        self.assertEqual(eval_result["status"], "PASS")
        self.assertGreaterEqual(eval_result["overall_score_percent"], 80.0)

    def test_structure_metric_complex_deck(self):
        p_path = self.data_dir / "test7_mixed_complex_pii.pptx"
        doc = extract_pptx(p_path)
        eval_result = evaluate_structure_retention(p_path, doc, target_percent=80.0)

        self.assertTrue(eval_result["passed"])
        self.assertEqual(eval_result["status"], "PASS")
        self.assertGreaterEqual(eval_result["overall_score_percent"], 80.0)


if __name__ == "__main__":
    unittest.main()
