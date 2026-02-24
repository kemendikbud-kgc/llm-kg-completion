"""Content filtering to skip administrative sections."""

import re
from dataclasses import dataclass


@dataclass
class FilterResult:
    """Result of filtering operation."""

    text: str  # Filtered text
    removed_sections: list[str]  # What was removed (for debugging)
    original_length: int
    filtered_length: int

    @property
    def reduction_percent(self) -> float:
        """Calculate percentage of content removed."""
        if self.original_length == 0:
            return 0.0
        return (1 - self.filtered_length / self.original_length) * 100


# Patterns for Indonesian curriculum books
SKIP_PATTERNS = [
    # Page numbers and headers
    r"^\s*\d+\s*$",  # Standalone page numbers
    r"^halaman\s+\d+",  # "Halaman X"
    r"^\s*-\s*\d+\s*-\s*$",  # "- 123 -" style
    r"^\s*\[\s*\d+\s*\]\s*$",  # "[123]" style
    # Credits and metadata
    r"(?i)^(penulis|editor|peninjau|kontributor)\s*:",
    r"(?i)^(penerbit|cetakan|isbn)\s*:",
    r"(?i)^(hak cipta|copyright)",
    r"(?i)^(diterbitkan oleh|published by)",
    r"(?i)^(kementerian|kemendikbud)",
    # Table of contents patterns
    r"(?i)^daftar isi",
    r"(?i)^table of contents",
    r"^\s*[IVX]+\.\s+.+\s+\d+$",  # "I. Chapter Name   12"
    r"^\s*[A-Z]\.\s+.+\s+\d+$",  # "A. Section Name   12"
    r"^\s*.+\.{3,}\s*\d+\s*$",  # "Topic Name....... 12"
    # References and bibliography
    r"(?i)^(daftar pustaka|referensi|bibliography)",
    r"(?i)^(sumber|source)\s*:",
    # Administrative sections
    r"(?i)^(kata pengantar|prakata|foreword)",
    r"(?i)^(ucapan terima kasih|acknowledgment)",
    r"(?i)^(tentang penulis|about the author)",
    r"(?i)^(glosarium|glossary)",
    r"(?i)^(indeks|index)$",
    r"(?i)^(lampiran|appendix)",
    # Common headers/footers
    r"(?i)^(buku|modul|kurikulum)\s+(siswa|guru|peserta didik)",
    r"(?i)^(fase|kelas|semester)\s+[A-Z0-9]+",
]

# Section headers that indicate non-content areas (entire chunks)
SKIP_SECTION_HEADERS = [
    "KATA PENGANTAR",
    "PRAKATA",
    "DAFTAR ISI",
    "DAFTAR PUSTAKA",
    "GLOSARIUM",
    "INDEKS",
    "UCAPAN TERIMA KASIH",
    "TENTANG PENULIS",
    "PROFIL PENULIS",
    "TIM PENYUSUN",
    "LAMPIRAN",
    "APPENDIX",
    "BIBLIOGRAFI",
    "REFERENSI",
    "TABLE OF CONTENTS",
    "ACKNOWLEDGMENT",
    "FOREWORD",
    "PREFACE",
]


def should_skip_line(line: str) -> bool:
    """Check if a single line should be skipped."""
    line = line.strip()
    if len(line) < 3:
        return True
    for pattern in SKIP_PATTERNS:
        if re.match(pattern, line, re.IGNORECASE):
            return True
    return False


def should_skip_chunk(chunk: str) -> bool:
    """Check if an entire chunk should be skipped (e.g., credits page)."""
    # If chunk starts with skip section header
    lines = chunk.strip().split("\n")
    if not lines:
        return True

    first_line = lines[0].strip().upper()
    for header in SKIP_SECTION_HEADERS:
        if header in first_line:
            return True

    # If >50% of lines are skippable patterns
    non_empty_lines = [line for line in lines if line.strip()]
    if not non_empty_lines:
        return True

    skip_count = sum(1 for line in non_empty_lines if should_skip_line(line))
    return skip_count / len(non_empty_lines) > 0.5


def filter_text(text: str) -> FilterResult:
    """Filter out administrative content from text.

    Args:
        text: Raw text to filter

    Returns:
        FilterResult with filtered text and statistics
    """
    lines = text.split("\n")
    filtered_lines = []
    removed = []

    for line in lines:
        if should_skip_line(line):
            if line.strip():
                removed.append(line.strip()[:50])
        else:
            filtered_lines.append(line)

    filtered_text = "\n".join(filtered_lines)

    return FilterResult(
        text=filtered_text,
        removed_sections=removed[:20],  # Keep first 20 for debugging
        original_length=len(text),
        filtered_length=len(filtered_text),
    )


def filter_chunks(chunks: list[str]) -> tuple[list[str], list[str]]:
    """Filter chunks, returning (kept_chunks, skipped_chunks).

    Args:
        chunks: List of text chunks

    Returns:
        Tuple of (kept chunks, skipped chunk summaries for debugging)
    """
    kept = []
    skipped = []
    for chunk in chunks:
        if should_skip_chunk(chunk):
            skipped.append(chunk[:100] + "..." if len(chunk) > 100 else chunk)
        else:
            kept.append(chunk)
    return kept, skipped
