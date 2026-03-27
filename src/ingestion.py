"""Step A: PDF ingestion - extract raw text and images from curriculum documents."""

import base64
import logging
import re
from dataclasses import dataclass, field

import fitz  # pymupdf

from src.config import VISION_DENSITY_THRESHOLD, VISION_IMAGE_COUNT_THRESHOLD
from src.filters import should_skip_chunk

logger = logging.getLogger(__name__)


@dataclass
class StructureEntry:
    """A Bab, SubBab, or SubSubBab entry parsed from Daftar Isi."""

    bab: str
    sub_bab: str | None
    sub_sub_bab: str | None = None  # 3rd level (1., 2., 3. under SubBab)
    page: int = 0  # 1-based page number from the ToC


@dataclass
class DocumentStructure:
    """Parsed Daftar Isi (Table of Contents) skeleton."""

    entries: list[StructureEntry] = field(default_factory=list)
    found: bool = False  # Whether a ToC was actually detected


# Regex patterns for Bab and SubBab detection
# Matches: "BAB 1  LISTRIK STATIS....1" or "BAB 1\tLISTRIK STATIS..1"
_BAB_PATTERN = re.compile(
    r"^(?:BAB|Bab)\s+([IVXLC]+|\d+)[\t\s.:–\-]*(.*?)(?:[\s.]{2,}\s*(\d+)\s*)?$",
    re.IGNORECASE,
)
# Matches: "1.1 Komponen Kimia Sel .... 5"
_SUBBAB_NUM_PATTERN = re.compile(
    r"^\s*(\d+\.\d+(?:\.\d+)?)[.\s]+(.*?)(?:[\s.]{2,}\s*(\d+)\s*)?$"
)
# Matches: "A.  Gaya Listrik .... 3" or "A.\t Gaya Listrik...3"
_SUBBAB_ALPHA_PATTERN = re.compile(r"^\s*([A-Z])\.\s+(.*?)(?:[\s.]{2,}\s*(\d+)\s*)?$")
# Matches: "1. Hukum Coulomb .....4" (single digit + title under SubBab)
_SUBBAB_FLAT_NUM_PATTERN = re.compile(r"^\s*(\d)\.\s+(.*?)(?:[\s.]{2,}\s*(\d+)\s*)?$")
_PAGE_NUM_PATTERN = re.compile(r"(\d+)\s*$")

# Lines in ToC to skip (page number lines, administrative entries)
_SKIP_PATTERN = re.compile(
    r"^(Rangkuman|Asesmen|Pengayaan|Refleksi|Kata Pengantar|Prakata|Petunjuk|Daftar Gambar|Daftar Tabel|[ivxlcIVXLC]+|[xivXIV]+)[\s.]*\d*$",
    re.IGNORECASE,
)


def _extract_page_from_next_line(lines: list[str], current_idx: int) -> tuple[int, int]:
    """Check if the next non-empty line is a pure page number.

    Used for Biology-style ToC where page numbers appear on SEPARATE lines.

    Returns (page_number, lines_to_skip).
    If no page found, returns (0, 0).
    """
    for offset in range(1, 4):  # Look ahead up to 3 lines
        if current_idx + offset >= len(lines):
            break
        next_line = lines[current_idx + offset].strip()
        if not next_line:
            continue
        # Check if it's a pure number (page number)
        if re.match(r"^\d+$", next_line):
            return int(next_line), offset
        # Not a number, stop looking
        break
    return 0, 0


def _is_valid_subbab_title(title: str) -> bool:
    """Check if a title looks like a valid SubBab title, not a species name.

    Valid SubBab titles start with a capitalized word.
    Species names like "melanogaster" start with lowercase.

    Examples:
    - "Definisi Bioteknologi" → first word "Definisi" capitalized → VALID
    - "Harapan dan Kenyataan" → first word "Harapan" capitalized → VALID
    - "melanogaster" → first word lowercase → INVALID (species name)
    - "sapiens" → first word lowercase → INVALID (species name)
    """
    if not title:
        return False  # Empty title is invalid

    title = title.strip()
    if not title:
        return False

    # First word must start with uppercase letter
    # Species epithets (melanogaster, sapiens) are always lowercase
    first_word = title.split()[0]
    if first_word[0].islower():
        return False

    return True


def _normalize_toc_lines(lines: list[str]) -> list[str]:
    """Join split TOC lines where letter prefix and title are on separate lines.

    Handles PDF extraction artifacts like:
      "A.    "        →  "A.  Definisi Evolusi"
      "Definisi Evolusi"

    Also deduplicates consecutive identical lines (e.g., two "A." lines).
    """
    result = []
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if not stripped:
            result.append(lines[i])
            i += 1
            continue

        # Check if this is a lone letter prefix: "A." / "B." etc. (with optional trailing whitespace)
        if re.match(r"^[A-Z]\.\s*$", stripped):
            # Look ahead for the title on the next non-empty, non-duplicate line
            j = i + 1
            while j < len(lines):
                next_stripped = lines[j].strip()
                if not next_stripped:
                    j += 1
                    continue
                # Skip duplicate letter prefix lines
                if next_stripped == stripped:
                    j += 1
                    continue
                # Skip if next line is ALSO a lone letter prefix (different letter)
                if re.match(r"^[A-Z]\.\s*$", next_stripped):
                    break
                # Found the title — join them
                result.append(f"  {stripped} {next_stripped}")
                i = j + 1
                break
            else:
                # No title found, keep as-is
                result.append(lines[i])
                i += 1
                continue
            # If we broke out of the while (next line is a different lone prefix), keep current as-is
            if i <= j - 1:
                result.append(lines[i])
                i += 1
        else:
            result.append(lines[i])
            i += 1

    return result


def parse_daftar_isi(raw_text: str) -> DocumentStructure:
    """Parse Daftar Isi (Table of Contents) from raw PDF text.

    Scans for a ToC section and extracts Bab/SubBab/SubSubBab entries with their
    page numbers. Returns a DocumentStructure that can be used to stamp text chunks.

    Handles Indonesian textbook formats where:
    - Bab lines: "BAB 1  TITLE....page" or "BAB 1\\tTITLE...page"
    - SubBab lines: "A.  Title....page" or "1.1 Title....page"
    - SubSubBab lines: "1. Title....page" (flat numeric under SubBab)
    - ToC may span multiple PDF pages (with page number lines in between)

    Supports both 2-level (Biology: Bab + SubBab) and 3-level (Physics/Chemistry:
    Bab + SubBab + SubSubBab) hierarchies.
    """
    lines = raw_text.splitlines()

    # Find ALL occurrences of "Daftar Isi" — use the last one (actual ToC, not references)
    toc_starts = [
        idx
        for idx, line in enumerate(lines)
        if re.search(r"daftar\s+isi|table\s+of\s+contents", line.strip(), re.IGNORECASE)
    ]
    if not toc_starts:
        return DocumentStructure(found=False)

    toc_start = toc_starts[-1]

    # Scan up to 300 lines; stop when we hit actual chapter content
    # (a BAB line with NO page number trailing it = real chapter heading, not ToC entry)
    toc_end = min(toc_start + 300, len(lines))
    bab_seen = 0
    for idx in range(toc_start + 1, toc_end):
        stripped = lines[idx].strip()
        # A bare "BAB X" line with no dots/page number = we've left the ToC
        if re.match(r"^(BAB|Bab)\s+[IVXLC\d]+\s*$", stripped):
            toc_end = idx
            break
        if _BAB_PATTERN.match(stripped):
            bab_seen += 1

    toc_lines = lines[toc_start + 1 : toc_end]
    toc_lines = _normalize_toc_lines(toc_lines)  # Join split letter+title lines

    # DEBUG: Log ToC lines to understand format
    logger.info("=== TOC LINES (first 30) ===")
    for i, line in enumerate(toc_lines[:30]):
        logger.info(f"  {i:3d}: {repr(line)}")
    logger.info("=== END TOC LINES ===")

    entries: list[StructureEntry] = []
    current_bab: str | None = None
    current_sub_bab: str | None = None

    for idx, line in enumerate(toc_lines):
        stripped = line.strip()
        if not stripped:
            continue
        # Skip pure page-number lines (e.g. "xii", "xiii", "12")
        if re.match(r"^[ivxlcIVXLC]+$", stripped) or re.match(r"^\d+$", stripped):
            continue
        # Skip administrative entries (Rangkuman, Asesmen, etc.)
        if _SKIP_PATTERN.match(stripped):
            continue

        # Try Bab line
        bab_match = _BAB_PATTERN.match(stripped)
        if bab_match:
            bab_num = bab_match.group(1)
            bab_title = (bab_match.group(2) or "").strip()
            page_str = bab_match.group(3)
            # Strip trailing dots/spaces from title
            bab_title = re.sub(r"[\s.]+$", "", bab_title)
            bab_title = re.sub(r"\s{2,}", " ", bab_title)  # collapse multiple spaces
            if not page_str:
                page_match = _PAGE_NUM_PATTERN.search(bab_title)
                if page_match:
                    page_str = page_match.group(1)
                    bab_title = bab_title[: page_match.start()].strip()
            page = int(page_str) if page_str else 0
            if page == 0:
                page, _ = _extract_page_from_next_line(toc_lines, idx)
            current_bab = (
                f"Bab {bab_num}: {bab_title}" if bab_title else f"Bab {bab_num}"
            )
            current_sub_bab = None  # Reset sub_bab when entering new Bab
            entries.append(
                StructureEntry(
                    bab=current_bab, sub_bab=None, sub_sub_bab=None, page=page
                )
            )
            continue

        if not current_bab:
            continue

        # Try SubBab: alphabetic style (A., B., C.) — check this before flat numeric
        alpha_match = _SUBBAB_ALPHA_PATTERN.match(stripped)
        if alpha_match:
            sub_letter = alpha_match.group(1)
            sub_title = re.sub(r"[\s.]+$", "", (alpha_match.group(2) or "").strip())
            sub_title = re.sub(r"\s{2,}", " ", sub_title)  # collapse multiple spaces
            page_str = alpha_match.group(3)
            # Validate: skip species names like "D. melanogaster"
            if not _is_valid_subbab_title(sub_title):
                continue
            if not page_str:
                page_match = _PAGE_NUM_PATTERN.search(stripped)
                page_str = page_match.group(1) if page_match else None
            page = int(page_str) if page_str else 0
            if page == 0:
                page, _ = _extract_page_from_next_line(toc_lines, idx)
            current_sub_bab = (
                f"{sub_letter}. {sub_title}" if sub_title else f"{sub_letter}."
            )
            entries.append(
                StructureEntry(
                    bab=current_bab,
                    sub_bab=current_sub_bab,
                    sub_sub_bab=None,
                    page=page,
                )
            )
            continue

        # Try SubBab: numeric style (1.1, 1.2) — this is NOT a SubSubBab
        sub_match = _SUBBAB_NUM_PATTERN.match(stripped)
        if sub_match:
            sub_num = sub_match.group(1)
            sub_title = re.sub(r"[\s.]+$", "", (sub_match.group(2) or "").strip())
            sub_title = re.sub(r"\s{2,}", " ", sub_title)  # collapse multiple spaces
            page_str = sub_match.group(3)
            if not page_str:
                page_match = _PAGE_NUM_PATTERN.search(stripped)
                page_str = page_match.group(1) if page_match else None
            page = int(page_str) if page_str else 0
            if page == 0:
                page, _ = _extract_page_from_next_line(toc_lines, idx)
            sub_bab = f"{sub_num} {sub_title}" if sub_title else sub_num
            current_sub_bab = sub_bab
            entries.append(
                StructureEntry(
                    bab=current_bab, sub_bab=sub_bab, sub_sub_bab=None, page=page
                )
            )
            continue

        # Try SubSubBab: flat numeric style (1., 2., 3.) — ONLY valid if we have a current_sub_bab
        if current_sub_bab:
            flat_match = _SUBBAB_FLAT_NUM_PATTERN.match(stripped)
            if flat_match:
                sub_num = flat_match.group(1)
                sub_title = re.sub(r"[\s.]+$", "", (flat_match.group(2) or "").strip())
                sub_title = re.sub(
                    r"\s{2,}", " ", sub_title
                )  # collapse multiple spaces
                page_str = flat_match.group(3)
                if not page_str:
                    page_match = _PAGE_NUM_PATTERN.search(stripped)
                    page_str = page_match.group(1) if page_match else None
                page = int(page_str) if page_str else 0
                if page == 0:
                    page, _ = _extract_page_from_next_line(toc_lines, idx)
                sub_sub_bab = f"{sub_num}. {sub_title}" if sub_title else f"{sub_num}."
                entries.append(
                    StructureEntry(
                        bab=current_bab,
                        sub_bab=current_sub_bab,
                        sub_sub_bab=sub_sub_bab,
                        page=page,
                    )
                )
                continue

    if not entries:
        return DocumentStructure(found=False)

    # Post-process: match entries with trailing page numbers
    # Biology-style ToC has all entries first, then all page numbers on separate lines
    entries = _assign_trailing_page_numbers(entries, toc_lines)

    return DocumentStructure(entries=entries, found=True)


def _assign_trailing_page_numbers(
    entries: list[StructureEntry], toc_lines: list[str]
) -> list[StructureEntry]:
    """Assign page numbers to entries that have page=0 using trailing number lines.

    Biology-style ToC format:
    - All entries listed with leader dots (no inline page numbers)
    - All page numbers on separate lines at the end

    This function matches entries with page=0 to trailing number lines positionally.
    """
    # Check if we have entries with missing page numbers
    entries_without_pages = [e for e in entries if e.page == 0]
    if not entries_without_pages:
        return entries

    # Collect trailing number lines from the end of toc_lines
    trailing_numbers: list[int] = []
    for line in reversed(toc_lines):
        stripped = line.strip()
        if re.match(r"^\d+$", stripped):
            trailing_numbers.insert(0, int(stripped))
        elif stripped:
            # Non-number line - stop collecting
            break

    # If we have matching counts, assign pages positionally
    if len(trailing_numbers) >= len(entries_without_pages):
        # Assign to entries with page=0
        num_idx = 0
        for entry in entries:
            if entry.page == 0 and num_idx < len(trailing_numbers):
                entry.page = trailing_numbers[num_idx]
                num_idx += 1

    return entries


_GLOS_PATTERN = re.compile(
    r"^([A-Za-z\u00C0-\u024F][^:–\-]{1,60}?)[\s]*(?::|–|-)\s*(.+)$"
)


def extract_glossary(raw_text: str) -> dict[str, str]:
    """Extract glossary terms from the Glosarium section of raw PDF text.

    Scans for the last 'Glosarium' or 'Glosari' section and parses
    ``term: definition`` or ``term — definition`` pairs.

    Returns a ``{term_lower: definition}`` dict. Empty dict if not found.
    """
    lines = raw_text.splitlines()

    glos_starts = [
        idx
        for idx, line in enumerate(lines)
        if re.search(r"glosari[um]*", line.strip(), re.IGNORECASE)
        and len(line.strip()) < 30  # section header, not inline mention
    ]
    if not glos_starts:
        return {}

    glos_start = glos_starts[-1]
    glos_end = min(glos_start + 500, len(lines))

    glossary: dict[str, str] = {}
    for line in lines[glos_start + 1 : glos_end]:
        stripped = line.strip()
        if not stripped:
            continue
        m = _GLOS_PATTERN.match(stripped)
        if m:
            term = m.group(1).strip()
            definition = m.group(2).strip()
            if term and definition and len(term) < 60:
                glossary[term.lower()] = definition

    return glossary


def extract_pages_for_subbab(
    pages: list[tuple[int, str]],
    doc_structure: DocumentStructure,
    bab: str,
    sub_bab: str | None,
    sub_sub_bab: str | None = None,
) -> str:
    """Return combined page text for a specific SubBab or SubSubBab section.

    Uses ToC page ranges to slice the ``pages`` list to the content window
    for the given ``bab``/``sub_bab``/``sub_sub_bab`` entry. Returns an empty
    string if the section is not found in the ToC or if ``pages`` is empty.
    """
    if not doc_structure.found or not doc_structure.entries or not pages:
        return ""

    target_idx: int | None = None
    for i, entry in enumerate(doc_structure.entries):
        if (
            entry.bab == bab
            and entry.sub_bab == sub_bab
            and entry.sub_sub_bab == sub_sub_bab
        ):
            target_idx = i
            break

    if target_idx is None:
        return ""

    start_page = doc_structure.entries[target_idx].page
    max_page = max(p for p, _ in pages) if pages else 1

    # Handle start_page = 0 (missing page number in ToC)
    if start_page <= 0:
        start_page = 1  # Default to first page

    if target_idx + 1 < len(doc_structure.entries):
        next_page = doc_structure.entries[target_idx + 1].page
        # Handle next entry with page=0 or invalid page
        if next_page > start_page:
            end_page = next_page - 1
        else:
            # Fallback: use max page (no upper bound)
            end_page = max_page
    else:
        end_page = max_page

    # Ensure valid range (end_page must be >= start_page)
    if end_page < start_page:
        end_page = max_page

    texts = [text for page_num, text in pages if start_page <= page_num <= end_page]
    return "\n".join(texts)


def get_structure_for_page(
    structure: DocumentStructure, page_num: int
) -> tuple[str | None, str | None, str | None]:
    """Return (bab_name, sub_bab_name, sub_sub_bab_name) for a given 1-based page number.

    Finds the nearest preceding entry in the ToC skeleton.
    """
    if not structure.found or not structure.entries:
        return None, None, None

    best_bab: str | None = None
    best_sub_bab: str | None = None
    best_sub_sub_bab: str | None = None

    for entry in structure.entries:
        if entry.page <= page_num:
            best_bab = entry.bab
            best_sub_bab = entry.sub_bab
            best_sub_sub_bab = entry.sub_sub_bab
        else:
            break

    return best_bab, best_sub_bab, best_sub_sub_bab


@dataclass
class PageClassification:
    """Classification result for a single PDF page."""

    page_num: int
    method: str  # "text" or "vision"
    text: str  # extracted text (may be empty for vision pages)
    reason: str  # why this classification was chosen


@dataclass
class VisionPage:
    """A vision-classified page with its rendered image and page number."""

    page_num: int  # 1-based
    image_b64: str  # base64-encoded PNG
    extracted_text: str = ""  # optional: text extracted from the page (may be sparse)


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF using pymupdf (drop-in replacement for PyPDF2)."""
    doc = fitz.open(pdf_path)
    pages = []
    for page in doc:
        pages.append(page.get_text() or "")
    doc.close()
    return "\n".join(pages)


def extract_pages_from_pdf(pdf_path: str) -> list[tuple[int, str]]:
    """Extract text per page from PDF.

    Returns:
        List of (page_num, text) tuples (1-based page numbers).
    """
    doc = fitz.open(pdf_path)
    result = []
    for i, page in enumerate(doc):
        result.append((i + 1, page.get_text() or ""))
    doc.close()
    return result


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


def ingest_pdf_enhanced_v2(
    pdf_path: str,
) -> tuple[str, list[VisionPage], list[PageClassification]]:
    """Enhanced ingestion with page-tracked vision images.

    Like ingest_pdf_enhanced() but returns VisionPage objects that preserve
    page numbers for vision-classified pages. This enables per-Bab vision
    extraction where vision pages are associated with their chapter.

    Returns:
        (text_content, vision_pages, classifications)
        - text_content: combined text from text-classified pages
        - vision_pages: VisionPage objects for vision-classified pages (with page_num)
        - classifications: per-page classification details
    """
    doc = fitz.open(pdf_path)
    classifications: list[PageClassification] = []
    text_pages: list[str] = []
    vision_pages: list[VisionPage] = []

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
            vision_pages.append(
                VisionPage(page_num=i + 1, image_b64=img_b64, extracted_text=text)
            )

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
        "Enhanced v2 ingestion: %d text pages, %d vision pages, %d skipped",
        sum(1 for c in classifications if c.method == "text"),
        len(vision_pages),
        sum(1 for c in classifications if c.method == "skip"),
    )
    return combined_text, vision_pages, classifications


def get_bab_page_range(
    doc_structure: DocumentStructure, bab_name: str
) -> tuple[int, int]:
    """Get the (start_page, end_page) range for a given Bab.

    Handles cases where ToC entries have page=0 (failed parsing).
    Falls back to inclusive defaults that match all pages.

    Returns (1, 999999) if the Bab is not found or has no valid page info.
    The end_page is INCLUSIVE.
    """
    if not doc_structure.found or not doc_structure.entries:
        return 1, 999999  # Default: all pages

    start_page = 1  # Default: start from page 1 (PDF pages are 1-based)
    end_page = 999999  # Default: no upper bound

    for i, entry in enumerate(doc_structure.entries):
        if (
            entry.bab == bab_name
            and entry.sub_bab is None
            and entry.sub_sub_bab is None
        ):
            # Use entry.page if > 0, otherwise look for first SubBab's page
            if entry.page > 0:
                start_page = entry.page
            else:
                # Fallback: find first SubBab under this Bab
                for j in range(i + 1, len(doc_structure.entries)):
                    sub_entry = doc_structure.entries[j]
                    if sub_entry.bab == bab_name and sub_entry.sub_bab:
                        if sub_entry.page > 0:
                            start_page = sub_entry.page
                            break
                    elif sub_entry.bab != bab_name:
                        break  # Moved to next Bab

            # Find the next Bab entry to determine end_page
            for j in range(i + 1, len(doc_structure.entries)):
                next_entry = doc_structure.entries[j]
                if next_entry.sub_bab is None and next_entry.sub_sub_bab is None:
                    if next_entry.page > start_page:
                        end_page = next_entry.page - 1
                    # else: keep end_page = 999999
                    break

            break

    # Ensure valid range (handle page=0 edge cases)
    if end_page <= 0 or end_page < start_page:
        end_page = 999999

    return start_page, end_page


def collect_bab_content(
    pages: list[tuple[int, str]],
    vision_pages: list[VisionPage] | None,
    doc_structure: DocumentStructure,
    bab_name: str,
) -> tuple[str, list[VisionPage]]:
    """Collect all text and vision pages for a specific Bab.

    Args:
        pages: List of (page_num, text) tuples from extract_pages_from_pdf()
        vision_pages: List of VisionPage objects (may be None or empty)
        doc_structure: DocumentStructure with ToC entries
        bab_name: Name of the Bab to collect content for

    Returns:
        (combined_text, vision_pages_for_bab)
        - combined_text: All text from pages in this Bab's range
        - vision_pages_for_bab: VisionPage objects whose page_num falls in this Bab
    """
    start_page, end_page = get_bab_page_range(doc_structure, bab_name)

    # Collect text pages
    texts = [text for page_num, text in pages if start_page <= page_num <= end_page]
    combined_text = "\n".join(texts)

    # Collect vision pages
    vision_for_bab: list[VisionPage] = []
    if vision_pages:
        for vp in vision_pages:
            if start_page <= vp.page_num <= end_page:
                vision_for_bab.append(vp)

    return combined_text, vision_for_bab


def get_subbab_names_for_bab(
    doc_structure: DocumentStructure, bab_name: str
) -> list[str]:
    """Get unique SubBab names for a given Bab from the ToC.

    Returns SubBab names in the order they appear in the ToC.
    """
    if not doc_structure.found or not doc_structure.entries:
        return []

    seen: set[str] = set()
    result: list[str] = []
    for entry in doc_structure.entries:
        if entry.bab == bab_name and entry.sub_bab and entry.sub_bab not in seen:
            seen.add(entry.sub_bab)
            result.append(entry.sub_bab)

    return result


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


# ─────────────────────────────────────────────────────────────────────────────
# ToC Verification Functions (inspired by PageIndex)
# ─────────────────────────────────────────────────────────────────────────────


def _extract_json_from_response(text: str) -> dict:
    """Extract JSON from LLM response, handling markdown code fences."""
    import json

    text = text.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]  # Remove first line (```json or ```)
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]  # Remove last line (```)
        text = "\n".join(lines)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


def verify_toc_entry(
    entry: StructureEntry,
    page_text: str,
    model: str = "gemini/gemini-2.5-flash",
) -> bool:
    """Use LLM to verify if a ToC entry appears on the expected page.

    Inspired by PageIndex's check_title_appearance() function.
    Uses fuzzy matching to handle OCR errors and spacing inconsistencies.

    Args:
        entry: The StructureEntry to verify
        page_text: The text content of the page to check
        model: LLM model to use for verification

    Returns:
        True if the entry appears on the page, False otherwise
    """
    import litellm

    # Build the section title
    title_parts = [entry.bab]
    if entry.sub_bab:
        title_parts.append(entry.sub_bab)
    if entry.sub_sub_bab:
        title_parts.append(entry.sub_sub_bab)
    section_title = " → ".join(title_parts)

    # Truncate page text to avoid token limits
    truncated_text = page_text[:2000] if len(page_text) > 2000 else page_text

    prompt = f"""Your job is to check if the given section appears or starts in the given page_text.

Note: do fuzzy matching, ignore any space inconsistency in the page_text.

The given section title is: {section_title}
The given page_text is:
{truncated_text}

Reply format:
{{
    "thinking": "<why do you think the section appears or starts in the page_text>",
    "answer": "yes" or "no"
}}

Directly return the final JSON structure. Do not output anything else."""

    try:
        response = litellm.completion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        content = response.choices[0].message.content or ""
        parsed = _extract_json_from_response(content)
        answer = parsed.get("answer", "no").lower()
        return answer == "yes"
    except Exception as e:
        logger.warning("verify_toc_entry failed for %s: %s", section_title, e)
        return False


def fix_toc_page_number(
    entry: StructureEntry,
    pages: list[tuple[int, str]],
    search_range: tuple[int, int],
    model: str = "gemini/gemini-2.5-flash",
) -> int | None:
    """Find the correct page number for a ToC entry using LLM.

    Inspired by PageIndex's single_toc_item_index_fixer() function.
    Searches within a range of pages to find where the section actually starts.

    Args:
        entry: The StructureEntry with incorrect page number
        pages: List of (page_num, text) tuples
        search_range: (start_page, end_page) range to search within
        model: LLM model to use

    Returns:
        The correct page number, or None if not found
    """
    import litellm

    start_page, end_page = search_range

    # Build the section title
    title_parts = [entry.bab]
    if entry.sub_bab:
        title_parts.append(entry.sub_bab)
    if entry.sub_sub_bab:
        title_parts.append(entry.sub_sub_bab)
    section_title = " → ".join(title_parts)

    # Build content with page markers
    content_parts = []
    page_dict = {p: t for p, t in pages}
    for page_num in range(start_page, end_page + 1):
        if page_num in page_dict:
            text = page_dict[page_num][:500]  # Truncate per page
            content_parts.append(f"<page_{page_num}>\n{text}\n</page_{page_num}>")

    content = "\n".join(content_parts)

    prompt = f"""You are given a section title and several pages of a document.
Your job is to find the page number where this section starts.

The section title is: {section_title}

Document pages (with page markers):
{content}

Reply format:
{{
    "thinking": "<explain which page contains the start of this section>",
    "page_number": <the page number where the section starts>
}}

Directly return the final JSON structure. Do not output anything else."""

    try:
        response = litellm.completion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        content = response.choices[0].message.content or ""
        parsed = _extract_json_from_response(content)
        page_num = parsed.get("page_number")
        if isinstance(page_num, int) and start_page <= page_num <= end_page:
            return page_num
        return None
    except Exception as e:
        logger.warning("fix_toc_page_number failed for %s: %s", section_title, e)
        return None


def verify_and_fix_toc(
    doc_structure: DocumentStructure,
    pages: list[tuple[int, str]],
    model: str = "gemini/gemini-2.5-flash",
    sample_size: int = 5,
) -> DocumentStructure:
    """Verify ToC entries and fix incorrect page numbers.

    Inspired by PageIndex's verify_toc() and fix_incorrect_toc() functions.
    Samples entries, verifies them with LLM, and fixes incorrect page numbers.

    Args:
        doc_structure: The parsed DocumentStructure
        pages: List of (page_num, text) tuples from the PDF
        model: LLM model to use for verification
        sample_size: Number of entries to sample for verification (0 = all)

    Returns:
        DocumentStructure with corrected page numbers
    """
    import random

    if not doc_structure.found or not doc_structure.entries:
        return doc_structure

    page_dict = {p: t for p, t in pages}
    entries = doc_structure.entries

    # Determine which entries to verify
    if sample_size > 0 and len(entries) > sample_size:
        indices_to_check = random.sample(range(len(entries)), sample_size)
    else:
        indices_to_check = list(range(len(entries)))

    logger.info("Verifying %d ToC entries...", len(indices_to_check))

    # Track entries with page=0 or incorrect page numbers
    incorrect_entries: list[tuple[int, StructureEntry]] = []

    for idx in indices_to_check:
        entry = entries[idx]

        # Skip entries with no page number
        if entry.page <= 0:
            incorrect_entries.append((idx, entry))
            continue

        # Verify entry appears on its page
        if entry.page in page_dict:
            page_text = page_dict[entry.page]
            is_correct = verify_toc_entry(entry, page_text, model)
            if not is_correct:
                logger.info(
                    "Entry '%s %s' not found on page %d, marking for fix",
                    entry.bab,
                    entry.sub_bab or "",
                    entry.page,
                )
                incorrect_entries.append((idx, entry))

    # Fix incorrect entries
    for idx, entry in incorrect_entries:
        # Determine search range: between previous and next valid entries
        prev_page = 1
        for i in range(idx - 1, -1, -1):
            if entries[i].page > 0:
                prev_page = entries[i].page
                break

        next_page = max(p for p, _ in pages) if pages else 999
        for i in range(idx + 1, len(entries)):
            if entries[i].page > 0:
                next_page = entries[i].page
                break

        # Find correct page
        correct_page = fix_toc_page_number(
            entry, pages, (prev_page, next_page), model
        )
        if correct_page is not None:
            logger.info(
                "Fixed entry '%s %s': page %d → %d",
                entry.bab,
                entry.sub_bab or "",
                entry.page,
                correct_page,
            )
            entries[idx] = StructureEntry(
                bab=entry.bab,
                sub_bab=entry.sub_bab,
                sub_sub_bab=entry.sub_sub_bab,
                page=correct_page,
            )

    return doc_structure
