"""Cadence Financial Group - Case Study 2: Text Analysis & PII Detection
Member 3: PowerPoint (PPTX) Extraction Engine & Structure Retention Evaluation
"""

from .extractor import PPTXExtractor
from .schema import ExtractedBlock, PPTXExtractionResult, Position
from .structure_metric import StructureMetricEngine, EvaluationResult

__version__ = "1.0.0"
__all__ = [
    "PPTXExtractor",
    "ExtractedBlock",
    "PPTXExtractionResult",
    "Position",
    "StructureMetricEngine",
    "EvaluationResult",
]
