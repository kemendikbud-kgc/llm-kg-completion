"""Step A: PDF ingestion - extract raw text from Capaian Pembelajaran documents."""

from PyPDF2 import PdfReader


def extract_text_from_pdf(pdf_path: str) -> str:
    reader = PdfReader(pdf_path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)
