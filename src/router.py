"""Document routing module for the cadence-pii-pipeline project.

Responsible for identifying input document types and routing them to the
appropriate extractor (DOCX, PDF, or PPTX).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, Optional, Union

from src.common.schema import Document


class RouterError(Exception):
    """Base exception for router-related errors."""
    pass


class UnsupportedFileTypeError(RouterError, ValueError):
    """Raised when an unsupported file extension or format is encountered."""
    pass


class ExtractorNotAvailableError(RouterError, RuntimeError):
    """Raised when the required extractor module or implementation is not available."""
    pass


# Default supported file extensions mapped to canonical file type names
SUPPORTED_EXTENSIONS: Dict[str, str] = {
    ".docx": "docx",
    ".pdf": "pdf",
    ".pptx": "pptx",
}


def _get_docx_extractor() -> Callable[..., Document]:
    """Lazily imports and returns the Member 1 DOCX extractor."""
    from src.extractors.docx_extractor import extract_docx
    return extract_docx


def _get_pdf_extractor() -> Callable[..., Document]:
    """Lazily imports and resolves Member 2's PDF extractor."""
    try:
        import src.extractors.pdf_extractor as pdf_mod
    except ImportError as exc:
        raise ExtractorNotAvailableError(
            f"PDF extractor module 'src.extractors.pdf_extractor' could not be imported: {exc}"
        ) from exc

    for attr in ("extract_pdf", "extract"):
        if hasattr(pdf_mod, attr) and callable(getattr(pdf_mod, attr)):
            return getattr(pdf_mod, attr)

    if hasattr(pdf_mod, "PDFExtractor"):
        extractor_cls = getattr(pdf_mod, "PDFExtractor")
        return lambda p, **kw: extractor_cls().extract(p, **kw)

    raise ExtractorNotAvailableError(
        "Module 'src.extractors.pdf_extractor' does not define an extractor entry point "
        "('extract_pdf', 'extract', or 'PDFExtractor'). Member 2 implementation may be pending."
    )


def _get_pptx_extractor() -> Callable[..., Document]:
    """Lazily imports and resolves Member 3's PPTX extractor."""
    try:
        import src.extractors.pptx_extractor as pptx_mod
    except ImportError as exc:
        raise ExtractorNotAvailableError(
            f"PPTX extractor module 'src.extractors.pptx_extractor' could not be imported: {exc}"
        ) from exc

    for attr in ("extract_pptx", "extract"):
        if hasattr(pptx_mod, attr) and callable(getattr(pptx_mod, attr)):
            return getattr(pptx_mod, attr)

    if hasattr(pptx_mod, "PPTXExtractor"):
        extractor_cls = getattr(pptx_mod, "PPTXExtractor")
        return lambda p, **kw: extractor_cls().extract(p, **kw)

    raise ExtractorNotAvailableError(
        "Module 'src.extractors.pptx_extractor' does not define an extractor entry point "
        "('extract_pptx', 'extract', or 'PPTXExtractor'). Member 3 implementation may be pending."
    )


class DocumentRouter:
    """Dispatches document extraction tasks to format-specific extractors."""

    def __init__(self) -> None:
        self._custom_extractors: Dict[str, Callable[..., Document]] = {}

    def register_extractor(self, file_type: str, extractor: Callable[..., Document]) -> None:
        """Registers or overrides an extractor for a given file type.

        Args:
            file_type: Canonical type or extension (e.g. 'docx', '.docx', 'custom').
            extractor: Callable accepting a file path and returning a Document.
        """
        canonical = file_type.lower().lstrip(".")
        self._custom_extractors[canonical] = extractor

    def detect_file_type(self, path: Union[str, Path]) -> str:
        """Determines the canonical file type of an input path based on its extension.

        Args:
            path: Path to the input document.

        Returns:
            Canonical file type string ('docx', 'pdf', 'pptx').

        Raises:
            UnsupportedFileTypeError: If the extension is empty or unsupported.
        """
        file_path = Path(path)
        ext = file_path.suffix.lower()

        if not ext:
            raise UnsupportedFileTypeError(
                f"File '{file_path.name}' has no file extension. "
                f"Supported extensions: {list(SUPPORTED_EXTENSIONS.keys())}"
            )

        if ext in SUPPORTED_EXTENSIONS:
            return SUPPORTED_EXTENSIONS[ext]

        clean_ext = ext.lstrip(".")
        if clean_ext in self._custom_extractors:
            return clean_ext

        raise UnsupportedFileTypeError(
            f"Unsupported file extension '{file_path.suffix}' for '{file_path.name}'. "
            f"Supported extensions: {list(SUPPORTED_EXTENSIONS.keys())}"
        )

    def is_supported(self, path: Union[str, Path]) -> bool:
        """Returns True if the file path has a supported extension, False otherwise."""
        try:
            self.detect_file_type(path)
            return True
        except UnsupportedFileTypeError:
            return False

    def get_extractor(self, file_type_or_path: Union[str, Path]) -> Callable[..., Document]:
        """Resolves the extractor callable for the given file type or file path.

        Args:
            file_type_or_path: File type name ('docx', 'pdf', 'pptx') or file path.

        Returns:
            A callable accepting a Path/str and returning a Document.

        Raises:
            UnsupportedFileTypeError: If the file type is unsupported.
            ExtractorNotAvailableError: If the extractor cannot be resolved.
        """
        candidate = str(file_type_or_path)

        # Check if candidate is a known file extension or filename
        if "." in candidate or Path(candidate).suffix:
            file_type = self.detect_file_type(candidate)
        else:
            file_type = candidate.lower().lstrip(".")

        # Check custom extractors first
        if file_type in self._custom_extractors:
            return self._custom_extractors[file_type]

        # Built-in dispatch with lazy import
        if file_type == "docx":
            return _get_docx_extractor()
        elif file_type == "pdf":
            return _get_pdf_extractor()
        elif file_type == "pptx":
            return _get_pptx_extractor()

        raise UnsupportedFileTypeError(
            f"No extractor registered for file type '{file_type}'. "
            f"Supported types: {list(SUPPORTED_EXTENSIONS.values())}"
        )

    def route_and_extract(self, path: Union[str, Path], **kwargs: Any) -> Document:
        """Routes the input document to the appropriate extractor and returns the extracted Document.

        Args:
            path: Path to the document.
            **kwargs: Additional parameters forwarded to the extractor.

        Returns:
            Extracted Document model.
        """
        file_path = Path(path)
        extractor = self.get_extractor(file_path)
        return extractor(file_path, **kwargs)


# Module-level default router singleton
_default_router = DocumentRouter()


def detect_file_type(path: Union[str, Path]) -> str:
    """Convenience function to detect file type using the default router."""
    return _default_router.detect_file_type(path)


def get_extractor(file_type_or_path: Union[str, Path]) -> Callable[..., Document]:
    """Convenience function to obtain an extractor using the default router."""
    return _default_router.get_extractor(file_type_or_path)


def route_and_extract(path: Union[str, Path], **kwargs: Any) -> Document:
    """Convenience function to route and extract a document using the default router."""
    return _default_router.route_and_extract(path, **kwargs)
