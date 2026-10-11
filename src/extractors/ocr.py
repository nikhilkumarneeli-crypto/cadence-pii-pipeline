 
"""Shared OCR and image preprocessing module for the cadence-pii-pipeline project (Member 2)."""

from __future__ import annotations

import io
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import cv2
import numpy as np
import pytesseract
from PIL import Image

from src.common.schema import TextBlock

LOW_CONFIDENCE_THRESHOLD: float = 0.75


def _configure_tesseract_cmd() -> bool:
    if shutil.which("tesseract"):
        return True
    common_win_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
    ]
    for p in common_win_paths:
        if os.path.exists(p):
            pytesseract.pytesseract.tesseract_cmd = p
            return True
    return False


def _load_bgr_or_gray(image_input: Union[bytes, np.ndarray, Image.Image, str, Path]) -> np.ndarray:
    if isinstance(image_input, (str, Path)):
        pil_img = Image.open(image_input).convert("RGB")
        return np.array(pil_img)
    if isinstance(image_input, bytes):
        pil_img = Image.open(io.BytesIO(image_input)).convert("RGB")
        return np.array(pil_img)
    if isinstance(image_input, Image.Image):
        return np.array(image_input.convert("RGB"))
    if isinstance(image_input, np.ndarray):
        return image_input.copy()
    raise ValueError(f"Unsupported image input type: {type(image_input)}")


def deskew_image(gray_img: np.ndarray) -> Tuple[np.ndarray, float]:
    _, inv = cv2.threshold(gray_img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    coords = np.column_stack(np.where(inv > 0))
    if len(coords) == 0:
        return gray_img, 0.0

    angle = cv2.minAreaRect(coords)[-1]
    angle = -(90.0 + angle) if angle < -45.0 else -angle

    if 0.5 <= abs(angle) <= 15.0:
        h, w = gray_img.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(
            gray_img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
        )
        return rotated, round(float(angle), 2)

    return gray_img, 0.0


def preprocess_image(
    image_input: Union[bytes, np.ndarray, Image.Image, str, Path],
    denoise: bool = True,
    deskew: bool = True,
    binarize: bool = True,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    raw = _load_bgr_or_gray(image_input)
    gray = cv2.cvtColor(raw, cv2.COLOR_RGB2GRAY) if len(raw.shape) == 3 else raw

    current = gray
    if denoise:
        current = cv2.fastNlMeansDenoising(current, None, h=10, templateWindowSize=7, searchWindowSize=21)

    skew_angle = 0.0
    if deskew:
        current, skew_angle = deskew_image(current)

    if binarize:
        _, current = cv2.threshold(current, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    prep_meta = {
        "denoised": denoise,
        "deskewed": deskew,
        "skew_angle_deg": skew_angle,
        "binarized": binarize,
        "image_shape": list(current.shape[:2]),
    }
    return current, prep_meta


def extract_ocr_blocks(
    image_input: Union[bytes, np.ndarray, Image.Image, str, Path],
    page_number: Optional[int] = 1,
    block_prefix: str = "ocr_para",
    start_order_index: int = 1,
    low_conf_threshold: float = LOW_CONFIDENCE_THRESHOLD,
) -> List[TextBlock]:
    cleaned_img, prep_meta = preprocess_image(image_input)
    tesseract_ready = _configure_tesseract_cmd()

    if not tesseract_ready:
        return [
            TextBlock(
                block_id=f"{block_prefix}_0",
                text="",
                page_number=page_number,
                metadata={
                    "block_type": "paragraph",
                    "source_type": "scanned_ocr",
                    "order_index": start_order_index,
                    "is_heading": False,
                    "heading_level": None,
                    "ocr_status": "tesseract_not_installed",
                    "confidence": 0.0,
                    "low_confidence_flag": True,
                    "low_confidence_words": [],
                    "preprocessing": prep_meta,
                },
            )
        ]

    try:
        data = pytesseract.image_to_data(cleaned_img, output_type=pytesseract.Output.DICT)
    except Exception as exc:
        return [
            TextBlock(
                block_id=f"{block_prefix}_0",
                text="",
                page_number=page_number,
                metadata={
                    "block_type": "paragraph",
                    "source_type": "scanned_ocr",
                    "order_index": start_order_index,
                    "is_heading": False,
                    "heading_level": None,
                    "ocr_status": f"ocr_error: {exc}",
                    "confidence": 0.0,
                    "low_confidence_flag": True,
                    "low_confidence_words": [],
                    "preprocessing": prep_meta,
                },
            )
        ]

    paragraphs: Dict[Tuple[int, int], Dict[str, Any]] = {}
    n_items = len(data.get("text", []))

    for i in range(n_items):
        word = str(data["text"][i]).strip()
        raw_conf = float(data["conf"][i])
        if not word or raw_conf < 0:
            continue

        conf = round(raw_conf / 100.0, 4)
        key = (int(data["block_num"][i]), int(data["par_num"][i]))
        left = float(data["left"][i])
        top = float(data["top"][i])
        width = float(data["width"][i])
        height = float(data["height"][i])

        if key not in paragraphs:
            paragraphs[key] = {
                "lines": {},
                "word_confidences": [],
                "low_conf_words": [],
                "left": left,
                "top": top,
                "right": left + width,
                "bottom": top + height,
            }

        p = paragraphs[key]
        line_num = int(data["line_num"][i])
        p["lines"].setdefault(line_num, []).append(word)
        p["word_confidences"].append({"word": word, "confidence": conf})

        if conf < low_conf_threshold:
            p["low_conf_words"].append({"word": word, "confidence": conf})

        p["left"] = min(p["left"], left)
        p["top"] = min(p["top"], top)
        p["right"] = max(p["right"], left + width)
        p["bottom"] = max(p["bottom"], top + height)

    sorted_paras = sorted(paragraphs.values(), key=lambda item: (round(item["top"] / 20.0), item["left"]))
    blocks: List[TextBlock] = []

    for idx, p in enumerate(sorted_paras):
        ordered_lines = [" ".join(p["lines"][ln]) for ln in sorted(p["lines"].keys())]
        para_text = "\n".join(ordered_lines).strip()
        if not para_text:
            continue

        confs = [w["confidence"] for w in p["word_confidences"]]
        avg_conf = round(sum(confs) / len(confs), 4) if confs else 0.0
        box_height = round(p["bottom"] - p["top"], 1)
        is_heading = len(ordered_lines) == 1 and len(para_text) < 80 and box_height > 24.0

        blocks.append(
            TextBlock(
                block_id=f"{block_prefix}_{idx}",
                text=para_text,
                page_number=page_number,
                metadata={
                    "block_type": "paragraph",
                    "source_type": "scanned_ocr",
                    "order_index": start_order_index + idx,
                    "is_heading": is_heading,
                    "heading_level": 1 if is_heading else None,
                    "position": {
                        "left": round(p["left"], 1),
                        "top": round(p["top"], 1),
                        "width": round(p["right"] - p["left"], 1),
                        "height": box_height,
                    },
                    "confidence": avg_conf,
                    "low_confidence_flag": len(p["low_conf_words"]) > 0,
                    "low_confidence_words": p["low_conf_words"],
                    "word_confidences": p["word_confidences"],
                    "lines": ordered_lines,
                    "preprocessing": prep_meta,
                },
            )
        )

    return blocks


def ocr_image(
    image_input: Union[bytes, np.ndarray, Image.Image, str, Path],
    page_number: Optional[int] = 1,
    low_conf_threshold: float = LOW_CONFIDENCE_THRESHOLD,
) -> Dict[str, Any]:
    blocks = extract_ocr_blocks(
        image_input=image_input,
        page_number=page_number,
        block_prefix=f"slide_{page_number or 1}_ocr",
        low_conf_threshold=low_conf_threshold,
    )
    texts = [b.text for b in blocks if b.text]
    confs = [b.metadata.get("confidence", 0.0) for b in blocks if b.text]
    low_conf_words = [w for b in blocks for w in b.metadata.get("low_confidence_words", [])]

    return {
        "text": "\n".join(texts),
        "confidence": round(sum(confs) / len(confs), 4) if confs else 0.0,
        "low_confidence_flag": len(low_conf_words) > 0,
        "low_confidence_words": low_conf_words,
        "blocks": blocks,
    }


def extract_text_from_image(
    image_input: Union[bytes, np.ndarray, Image.Image, str, Path],
    low_conf_threshold: float = LOW_CONFIDENCE_THRESHOLD,
) -> str:
    return ocr_image(image_input, low_conf_threshold=low_conf_threshold)["text"]


class TesseractOCRAdapter:
    def __init__(self, low_conf_threshold: float = LOW_CONFIDENCE_THRESHOLD) -> None:
        self.low_conf_threshold = low_conf_threshold

    def extract_text(self, image_input: Union[bytes, np.ndarray, Image.Image, str, Path]) -> Dict[str, Any]:
        return ocr_image(image_input, low_conf_threshold=self.low_conf_threshold)


ocr_image_bytes = ocr_image
 