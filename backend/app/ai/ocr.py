"""
OCR / text-extraction pipeline.

Priority: PaddleOCR (if installed) → pdfplumber native text layer (demo
PDFs are text-based; this is the offline path) → pypdf fallback.

Returns extracted text per page + a confidence estimate + the source name
so the UI can show exactly how the text was obtained.
"""
from __future__ import annotations

from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


def extract_text_from_pdf(path: str) -> dict[str, Any]:
    """
    Returns: {pages: [{page, text}], source, confidence}
    source ∈ {paddleocr, pdfplumber, pypdf}
    """
    try:
        return _paddleocr(path)
    except Exception:
        pass
    try:
        return _pdfplumber(path)
    except Exception as exc:
        logger.info("pdfplumber failed (%s) — trying pypdf", exc)
    try:
        return _pypdf(path)
    except Exception as exc:
        logger.warning("all text extractors failed on %s: %s", path, exc)
        raise


def _pdfplumber(path: str) -> dict[str, Any]:
    import pdfplumber

    pages: list[dict[str, Any]] = []
    total_chars = 0
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            total_chars += len(text)
            pages.append({"page": i + 1, "text": text})
    return {
        "pages": pages,
        "source": "pdfplumber",
        "confidence": min(0.99, 0.7 + total_chars / 2000),
    }


def _pypdf(path: str) -> dict[str, Any]:
    from pypdf import PdfReader

    reader = PdfReader(path)
    pages = []
    total = 0
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        total += len(text)
        pages.append({"page": i + 1, "text": text})
    return {"pages": pages, "source": "pypdf", "confidence": min(0.99, 0.6 + total / 2000)}


def _paddleocr(path: str) -> dict[str, Any]:
    """PaddleOCR image-based extraction (optional heavy dependency)."""
    from paddleocr import PaddleOCR  # type: ignore

    ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
    import fitz  # PyMuPDF for rasterization

    doc = fitz.open(path)
    pages = []
    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=200)
        img_path = f"/tmp/page_{i}.png"
        pix.save(img_path)
        result = ocr.ocr(img_path, cls=True)
        text = "\n".join(
            line[1][0] for line in (result[0] or []) if line and len(line) > 1
        )
        pages.append({"page": i + 1, "text": text})
    return {"pages": pages, "source": "paddleocr", "confidence": 0.85}