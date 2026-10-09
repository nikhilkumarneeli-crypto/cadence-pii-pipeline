"""Orchestration pipeline module for the cadence-pii-pipeline project.

Coordinates document ingestion, routing, extraction, PII detection, and redaction.
Serves as the primary integration entry point connecting:
- Ingestion and Format Routing (Member 1)
- Format-specific Extractors (DOCX: Member 1, PDF: Member 2, PPTX: Member 3)
- PII Detection Engine (Member 4)
- Redaction and Reporting (Member 5)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from src.common.schema import Document, PIIEntity, PipelineResult, Redaction
from src.router import DocumentRouter, _default_router


class PipelineError(Exception):
    """Base exception for pipeline execution errors."""
    pass


class PipelineExecutionError(PipelineError):
    """Raised when an error occurs during pipeline execution."""
    pass


class InvalidComponentError(PipelineError, TypeError):
    """Raised when an invalid or incompatible detector/redactor component is provided."""
    pass


class PIIPipeline:
    """End-to-end document processing pipeline for PII detection and redaction."""

    def __init__(
        self,
        router: Optional[DocumentRouter] = None,
        default_detector: Optional[Any] = None,
        default_redactor: Optional[Any] = None,
    ) -> None:
        """Initializes the pipeline with routing and optional default processing stages.

        Args:
            router: DocumentRouter instance for dispatching extractors. Defaults to module router.
            default_detector: Optional default PII detector component or callable.
            default_redactor: Optional default redactor component or callable.
        """
        self.router = router if router is not None else _default_router
        self.default_detector = default_detector
        self.default_redactor = default_redactor

        if default_detector is not None:
            self._validate_detector(default_detector)
        if default_redactor is not None:
            self._validate_redactor(default_redactor)

    def process(
        self,
        input_path: Union[str, Path],
        detector: Optional[Any] = None,
        redactor: Optional[Any] = None,
        document_id: Optional[str] = None,
    ) -> PipelineResult:
        """Processes an input document through extraction and optional detection/redaction.

        Args:
            input_path: Path to the input document.
            detector: Optional detector component or callable overriding the default.
            redactor: Optional redactor component or callable overriding the default.
            document_id: Optional explicit identifier for the document.

        Returns:
            PipelineResult containing the extracted document, detected entities,
            and redactions.

        Raises:
            FileNotFoundError: If the input file does not exist.
            ValueError: If input path is not a file or has an invalid format.
            UnsupportedFileTypeError: If the file type is not supported.
            ExtractorNotAvailableError: If the format extractor is not available.
            InvalidComponentError: If a supplied detector or redactor is invalid.
            PipelineExecutionError: If stage execution fails.
        """
        file_path = Path(input_path)

        # 1. Validate file existence
        if not file_path.exists():
            raise FileNotFoundError(f"Input document not found: {file_path}")

        if not file_path.is_file():
            raise ValueError(f"Input path is not a regular file: {file_path}")

        # 2. Resolve active detector and redactor
        active_detector = detector if detector is not None else self.default_detector
        active_redactor = redactor if redactor is not None else self.default_redactor

        if active_detector is not None:
            self._validate_detector(active_detector)
        if active_redactor is not None:
            self._validate_redactor(active_redactor)

        # 3. Document Extraction via Router
        document = self.router.route_and_extract(file_path, document_id=document_id)

        stages_executed = ["extraction"]
        is_empty = len(document.blocks) == 0

        # 4. Optional Detection Stage (Member 4 Integration Point)
        detected_entities: List[PIIEntity] = []
        if active_detector is not None:
            detected_entities = self._run_detection(active_detector, document)
            stages_executed.append("detection")

        # 5. Optional Redaction Stage (Member 5 Integration Point)
        redactions: List[Redaction] = []
        redacted_text: Optional[str] = None
        if active_redactor is not None:
            redactions, redacted_text = self._run_redaction(
                active_redactor, document, detected_entities
            )
            stages_executed.append("redaction")

        # 6. Assemble and return PipelineResult
        pipeline_metadata: Dict[str, Any] = {
            "source_path": str(file_path.resolve()),
            "file_type": document.file_type,
            "stages_executed": stages_executed,
            "is_empty": is_empty,
            "block_count": len(document.blocks),
            "detected_entities_count": len(detected_entities),
            "redactions_count": len(redactions),
        }

        return PipelineResult(
            document=document,
            detected_entities=detected_entities,
            redactions=redactions,
            redacted_text=redacted_text,
            metadata=pipeline_metadata,
        )

    def _validate_detector(self, detector: Any) -> None:
        """Validates that the detector implements a callable interface or detect/analyze method."""
        has_detect = hasattr(detector, "detect") and callable(getattr(detector, "detect"))
        has_analyze = hasattr(detector, "analyze") and callable(getattr(detector, "analyze"))
        is_fn = callable(detector)

        if not (has_detect or has_analyze or is_fn):
            raise InvalidComponentError(
                f"Detector '{detector}' is invalid: must be callable or provide a 'detect' or 'analyze' method."
            )

    def _validate_redactor(self, redactor: Any) -> None:
        """Validates that the redactor implements a callable interface or redact method."""
        has_redact = hasattr(redactor, "redact") and callable(getattr(redactor, "redact"))
        is_fn = callable(redactor)

        if not (has_redact or is_fn):
            raise InvalidComponentError(
                f"Redactor '{redactor}' is invalid: must be callable or provide a 'redact' method."
            )

    def _run_detection(self, detector: Any, document: Document) -> List[PIIEntity]:
        """Executes the detection stage using the provided detector."""
        try:
            if hasattr(detector, "detect") and callable(getattr(detector, "detect")):
                result = detector.detect(document)
            elif hasattr(detector, "analyze") and callable(getattr(detector, "analyze")):
                result = detector.analyze(document)
            elif callable(detector):
                result = detector(document)
            else:
                raise InvalidComponentError(f"Cannot invoke detector '{detector}'.")
        except Exception as exc:
            if isinstance(exc, (InvalidComponentError, PipelineError)):
                raise
            raise PipelineExecutionError(f"PII detection stage failed: {exc}") from exc

        if not isinstance(result, list):
            raise PipelineExecutionError(
                f"Detector returned unexpected type '{type(result).__name__}'. Expected list of PIIEntity."
            )

        return result

    def _run_redaction(
        self, redactor: Any, document: Document, entities: List[PIIEntity]
    ) -> Tuple[List[Redaction], Optional[str]]:
        """Executes the redaction stage using the provided redactor."""
        try:
            if hasattr(redactor, "redact") and callable(getattr(redactor, "redact")):
                result = redactor.redact(document, entities)
            elif callable(redactor):
                result = redactor(document, entities)
            else:
                raise InvalidComponentError(f"Cannot invoke redactor '{redactor}'.")
        except Exception as exc:
            if isinstance(exc, (InvalidComponentError, PipelineError)):
                raise
            raise PipelineExecutionError(f"Redaction stage failed: {exc}") from exc

        # Unpack various result structures gracefully
        redactions: List[Redaction] = []
        redacted_text: Optional[str] = None

        if isinstance(result, tuple):
            if len(result) >= 2:
                redactions, redacted_text = result[0], result[1]
            elif len(result) == 1:
                redactions = result[0]
        elif isinstance(result, list):
            redactions = result
        elif hasattr(result, "redactions"):
            redactions = getattr(result, "redactions", [])
            redacted_text = getattr(result, "redacted_text", None)
        elif isinstance(result, dict):
            redactions = result.get("redactions", [])
            redacted_text = result.get("redacted_text", None)
        else:
            raise PipelineExecutionError(
                f"Redactor returned unrecognized type '{type(result).__name__}'."
            )

        return redactions, redacted_text


# Module-level convenience pipeline instance
_default_pipeline = PIIPipeline()


def run_pipeline(
    input_path: Union[str, Path],
    detector: Optional[Any] = None,
    redactor: Optional[Any] = None,
    router: Optional[DocumentRouter] = None,
    document_id: Optional[str] = None,
) -> PipelineResult:
    """Convenience function to run the PII pipeline on a document.

    Args:
        input_path: Path to the input document.
        detector: Optional detector component or callable.
        redactor: Optional redactor component or callable.
        router: Optional custom router instance.
        document_id: Optional explicit identifier for the document.

    Returns:
        PipelineResult with document, detected entities, and redactions.
    """
    if router is not None or detector is not None or redactor is not None:
        pipeline = PIIPipeline(router=router, default_detector=detector, default_redactor=redactor)
        return pipeline.process(input_path, document_id=document_id)
    return _default_pipeline.process(input_path, document_id=document_id)
