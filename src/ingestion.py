"""Step A: PDF ingestion - extract raw text and images from curriculum documents."""

import base64
import logging
from dataclasses import dataclass

import fitz  # pymupdf

from src.config import VISION_DENSITY_THRESHOLD, VISION_IMAGE_COUNT_THRESHOLD
from src.filters import should_skip_chunk

logger = logging.getLogger(__name__)


@dataclass
class PageClassification:
    """Classification result for a single PDF page."""

    page_num: int
    method: str  # "text" or "vision"
    text: str  # extracted text (may be empty for vision pages)
    reason: str  # why this classification was chosen


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF using pymupdf (drop-in replacement for PyPDF2)."""
    doc = fitz.open(pdf_path)
    pages = []
    for page in doc:
        pages.append(page.get_text() or "")
    doc.close()
    return "\n".join(pages)


def _classify_page(page: fitz.Page) -> str:
    """Classify a page as 'text' or 'vision' based on content heuristics.

    Returns:
        'text' or 'vision'
    """
    text = page.get_text() or ""

    # Check if page is administrative (skip entirely)
    if should_skip_chunk(text):
        return "skip"

    # Check embedded image count
    images = page.get_images(full=True)
    if len(images) >= VISION_IMAGE_COUNT_THRESHOLD:
        return "vision"

    # Check text density
    rect = page.rect
    area = rect.width * rect.height
    if area > 0:
        density = len(text) / area
        if density < VISION_DENSITY_THRESHOLD:
            return "vision"

    # Check for formula characters (Greek, math operators, sub/superscripts)
    formula_count = sum(
        1
        for ch in text
        if (
            "\u0391" <= ch <= "\u03c9"  # Greek
            or "\u2200" <= ch <= "\u22ff"  # Math operators
            or "\u2080" <= ch <= "\u209f"  # Subscripts/superscripts
        )
    )
    if formula_count > 10:
        return "vision"

    return "text"


def _render_page_base64(page: fitz.Page, dpi: int = 150) -> str:
    """Render a PDF page to a base64-encoded PNG string."""
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat)
    png_bytes = pix.tobytes("png")
    return base64.b64encode(png_bytes).decode("ascii")


def ingest_pdf_enhanced(
    pdf_path: str,
) -> tuple[str, list[str], list[PageClassification]]:
    """Enhanced ingestion: text extraction + auto-detect pages needing vision.

    Returns:
        (text_content, vision_images_b64, classifications)
        - text_content: combined text from text-classified pages
        - vision_images_b64: base64 PNGs for vision-classified pages
        - classifications: per-page classification details
    """
    doc = fitz.open(pdf_path)
    classifications: list[PageClassification] = []
    text_pages: list[str] = []
    vision_images: list[str] = []

    for i, page in enumerate(doc):
        classification = _classify_page(page)
        text = page.get_text() or ""

        if classification == "skip":
            classifications.append(
                PageClassification(
                    page_num=i + 1,
                    method="skip",
                    text="",
                    reason="Administrative content",
                )
            )
        elif classification == "vision":
            img_b64 = _render_page_base64(page)
            vision_images.append(img_b64)

            # Determine reason
            images = page.get_images(full=True)
            rect = page.rect
            area = rect.width * rect.height
            density = len(text) / area if area > 0 else 0
            if len(images) >= VISION_IMAGE_COUNT_THRESHOLD:
                reason = f"{len(images)} embedded images"
            elif density < VISION_DENSITY_THRESHOLD:
                reason = f"Low text density ({density:.4f})"
            else:
                reason = "Formula characters detected"

            classifications.append(
                PageClassification(
                    page_num=i + 1,
                    method="vision",
                    text=text,
                    reason=reason,
                )
            )
        else:
            text_pages.append(text)
            classifications.append(
                PageClassification(
                    page_num=i + 1,
                    method="text",
                    text=text,
                    reason="Normal text content",
                )
            )

    doc.close()

    combined_text = "\n".join(text_pages)
    logger.info(
        "Enhanced ingestion: %d text pages, %d vision pages, %d skipped",
        sum(1 for c in classifications if c.method == "text"),
        sum(1 for c in classifications if c.method == "vision"),
        sum(1 for c in classifications if c.method == "skip"),
    )
    return combined_text, vision_images, classifications


def ingest_pdf_full_vision(pdf_path: str) -> list[str]:
    """Full vision ingestion: render all content pages as images.

    Returns:
        List of base64-encoded PNG strings (admin pages skipped).
    """
    doc = fitz.open(pdf_path)
    images: list[str] = []
    skipped = 0

    for page in doc:
        text = page.get_text() or ""
        if should_skip_chunk(text):
            skipped += 1
            continue
        images.append(_render_page_base64(page))

    doc.close()
    logger.info(
        "Full vision ingestion: %d content pages, %d skipped", len(images), skipped
    )
    return images
