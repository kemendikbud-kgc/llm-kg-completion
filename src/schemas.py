"""Pydantic models for structured LLM extraction."""

from typing import Literal

from pydantic import BaseModel

BloomLevel = Literal["remember", "understand", "apply", "analyze", "evaluate", "create"]


class SubKonsep(BaseModel):
    name: str
    description: str
    bloom_level: BloomLevel | None = None


# Backward-compat alias
SubTopic = SubKonsep


class Konsep(BaseModel):
    name: str
    description: str
    bloom_level: BloomLevel | None = None
    sub_konsep: list[SubKonsep] = []


# Backward-compat alias
Topic = Konsep


class MataPelajaran(BaseModel):
    """Indonesian curriculum subject (Mata Pelajaran)."""

    name: str  # e.g., "Fisika", "Biologi", "Kimia"
    phase: str = ""  # "E" (Kelas X) or "F" (Kelas XI-XII)


# Backward-compat alias
Subject = MataPelajaran

# Common subjects for Indonesian high school curriculum
SUBJECT_CHOICES = [
    "Fisika",
    "Kimia",
    "Biologi",
    "Matematika",
    "Bahasa Indonesia",
    "Bahasa Inggris",
    "Sejarah",
    "Geografi",
    "Ekonomi",
    "Sosiologi",
    "Informatika",
    "Other",
]

# Kurikulum Merdeka phases
PHASE_CHOICES = {
    "E": "Fase E (Kelas X)",
    "F": "Fase F (Kelas XI-XII)",
}

# Textbook class levels
KELAS_CHOICES = ["X", "XI", "XII"]


class KonsepExtraction(BaseModel):
    mata_pelajaran: MataPelajaran | None = None
    bab_name: str | None = None  # Chapter/section name detected from text
    konsep: list[Konsep]


# Backward-compat alias
TopicExtraction = KonsepExtraction
