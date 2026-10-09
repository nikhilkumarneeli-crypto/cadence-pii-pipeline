"""Image OCR Adapter & Extraction Module for Member 3 PPTX Engine.
Cadence Financial Group - Case Study 2: Text Analysis & PII Detection.

Detects images embedded in slides, provides a clean adapter interface for OCR,
checks local Tesseract availability, supports Member 2 OCR integration,
and provides transparent status reporting with clear installation instructions.
"""

from __future__ import annotations
import os
import io
import shutil
import logging
from typing import Optional, Tuple, Dict, Any, List
from pathlib import Path
from PIL import Image
import pptx
from pptx.enum.shapes import MSO_SHAPE_TYPE

from .schema import ExtractedBlock, Position
from .shape_extractor import extract_shape_position

logger = logging.getLogger(__name__)


TESSERACT_WINDOWS_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Tesseract-OCR\tesseract.exe"),
    os.path.expandvars(r"%PROGRAMFILES%\Tesseract-OCR\tesseract.exe"),
]


def find_tesseract_executable() -> Optional[str]:
    """Check PATH and common Windows installation locations for tesseract.exe."""
    which_path = shutil.which("tesseract")
    if which_path:
        return which_path

    for candidate in TESSERACT_WINDOWS_PATHS:
        if os.path.isfile(candidate):
            return candidate

    return None


class BaseOCRAdapter:
    """Abstract interface for OCR providers."""

    def is_available(self) -> bool:
        raise NotImplementedError

    def get_status_message(self) -> str:
        raise NotImplementedError

    def run_ocr(self, image_bytes: bytes) -> Tuple[str, float, Dict[str, Any]]:
        """Process image bytes and return (extracted_text, confidence, metadata)."""
        raise NotImplementedError


class Member2OCRAdapter(BaseOCRAdapter):
    """Adapter to reuse Member 2's OCR function if present in the repository."""

    def __init__(self):
        self._member2_func = None
        self._detect_member2()

    def _detect_member2(self):
        # Look for typical Member 2 module exports
        candidate_modules = [
            ("member2.ocr", "run_ocr"),
            ("member2_pdf.ocr", "extract_text_ocr"),
            ("pdf_extractor.ocr", "ocr_image"),
            ("src.member2.ocr", "run_ocr"),
        ]
        for mod_name, func_name in candidate_modules:
            try:
                mod = __import__(mod_name, fromlist=[func_name])
                self._member2_func = getattr(mod, func_name, None)
                if self._member2_func:
                    break
            except ImportError:
                continue

    def is_available(self) -> bool:
        return self._member2_func is not None

    def get_status_message(self) -> str:
        if self.is_available():
            return "Member 2 shared OCR module detected and integrated."
        return "Member 2 OCR module not yet present locally (standby for shared OCR integration)."

    def run_ocr(self, image_bytes: bytes) -> Tuple[str, float, Dict[str, Any]]:
        if not self.is_available():
            return "", 0.0, {"status": "member2_ocr_not_available"}
        try:
            res = self._member2_func(image_bytes)
            # Normalize response from Member 2
            if isinstance(res, tuple):
                text, conf = res[0], float(res[1])
            elif isinstance(res, dict):
                text = res.get("text", "")
                conf = float(res.get("confidence", 0.9))
            else:
                text = str(res)
                conf = 0.9
            return text.strip(), conf, {"engine": "member2_shared"}
        except Exception as e:
            return "", 0.0, {"status": f"member2_ocr_error: {str(e)}"}


class TesseractOCRAdapter(BaseOCRAdapter):
    """Local Tesseract OCR adapter via pytesseract."""

    def __init__(self):
        self.tesseract_cmd = find_tesseract_executable()
        self._pytesseract_available = False
        try:
            import pytesseract
            self._pytesseract = pytesseract
            if self.tesseract_cmd:
                self._pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
            self._pytesseract_available = True
        except ImportError:
            self._pytesseract = None

    def is_available(self) -> bool:
        return bool(self._pytesseract_available and self.tesseract_cmd and os.path.isfile(self.tesseract_cmd))

    def get_status_message(self) -> str:
        if self.is_available():
            return f"Tesseract OCR is active: {self.tesseract_cmd}"
        return (
            "Tesseract OCR binary not found on local system.\n"
            "Installation Instructions for Windows:\n"
            "  1. Run in PowerShell: winget install UB-Mannheim.TesseractOCR\n"
            "     OR download installer from: https://github.com/UB-Mannheim/tesseract/wiki\n"
            "  2. Add 'C:\\Program Files\\Tesseract-OCR' to Windows PATH\n"
            "  3. Restart PowerShell / VS Code terminal."
        )

    def run_ocr(self, image_bytes: bytes) -> Tuple[str, float, Dict[str, Any]]:
        if not self.is_available():
            return "", 0.0, {
                "status": "unavailable",
                "reason": "tesseract_binary_not_found",
                "instructions": self.get_status_message()
            }

        try:
            img = Image.open(io.BytesIO(image_bytes))
            # Image pre-processing: convert RGBA/palette to RGB
            if img.mode not in ("L", "RGB"):
                img = img.convert("RGB")

            # Extract detailed data for confidence calculation
            data = self._pytesseract.image_to_data(img, output_type=self._pytesseract.Output.DICT)
            text = self._pytesseract.image_to_string(img).strip()

            confidences = [
                float(c) for c in data.get("conf", [])
                if str(c).strip() not in ("-1", "")
            ]
            avg_conf = (sum(confidences) / len(confidences) / 100.0) if confidences else (0.85 if text else 0.0)

            return text, round(avg_conf, 4), {
                "engine": "pytesseract",
                "tesseract_path": self.tesseract_cmd,
                "word_count": len(text.split()),
                "status": "success"
            }
        except Exception as e:
            return "", 0.0, {
                "status": "error",
                "error": str(e)
            }


class MockOCRAdapter(BaseOCRAdapter):
    """Mock OCR adapter for automated unit testing and synthetic test verification."""

    def __init__(self, predefined_text: str = "SYNTHETIC OCR TEXT", confidence: float = 0.95):
        self.predefined_text = predefined_text
        self.confidence = confidence

    def is_available(self) -> bool:
        return True

    def get_status_message(self) -> str:
        return "Mock OCR Adapter active for testing."

    def run_ocr(self, image_bytes: bytes) -> Tuple[str, float, Dict[str, Any]]:
        return self.predefined_text, self.confidence, {"engine": "mock_ocr", "status": "success"}


class ImageOCRExtractor:
    """Extracts images from PowerPoint shapes and routes to available OCR adapter."""

    def __init__(self, file_name: str, ocr_adapter: Optional[BaseOCRAdapter] = None):
        self.file_name = file_name
        # Fallback hierarchy: Member 2 shared -> Local Tesseract
        if ocr_adapter:
            self.adapter = ocr_adapter
        else:
            m2 = Member2OCRAdapter()
            if m2.is_available():
                self.adapter = m2
            else:
                self.adapter = TesseractOCRAdapter()

    def get_status(self) -> Dict[str, Any]:
        return {
            "is_available": self.adapter.is_available(),
            "status_message": self.adapter.get_status_message(),
            "adapter_type": self.adapter.__class__.__name__,
        }

    def extract_from_picture(
        self,
        shape: Any,
        slide_num: int,
        slide_id: Optional[int],
        image_index: int,
        order_counter: int,
    ) -> Tuple[Optional[ExtractedBlock], int]:
        """Process picture shape, extract image bytes, and invoke OCR."""
        if shape.shape_type != MSO_SHAPE_TYPE.PICTURE and not hasattr(shape, "image"):
            return None, order_counter

        pos = extract_shape_position(shape)
        image = shape.image
        image_bytes = image.blob
        ext = image.ext

        # Run OCR
        text, confidence, ocr_info = self.adapter.run_ocr(image_bytes)

        order_counter += 1
        block_id = f"s{slide_num}_img_{image_index}"
        ctx_group_id = f"s{slide_num}_img_ctx_{image_index}"

        ocr_metadata = {
            "image_index": image_index,
            "format": ext,
            "ocr_status": ocr_info.get("status", "processed"),
            "ocr_confidence": confidence,
            "ocr_details": ocr_info,
        }

        # Store block matching section 9 requirement:
        # { "block_type": "image_ocr", "slide_number": 3, "image_index": 1, "text": "...", "ocr_confidence": 0.94 }
        block = ExtractedBlock(
            file=self.file_name,
            slide=slide_num,
            section=None,
            block_id=block_id,
            block_type="image_ocr",
            text=text,
            position=pos,
            order=order_counter,
            context_group_id=ctx_group_id,
            source_type="image_ocr",
            slide_id=slide_id,
            shape_id=shape.shape_id,
            confidence=confidence,
            ocr_metadata=ocr_metadata,
        )

        return block, order_counter
