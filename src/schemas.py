"""Pydantic models for structured LLM extraction."""

from typing import Literal

from pydantic import BaseModel

BloomLevel = Literal["remember", "understand", "apply", "analyze", "evaluate", "create"]

# Allowed relation types for inline KG extraction
RelationType = Literal[
    "MENDEFINISIKAN",
    "MENYEBABKAN",
    "MEMUNGKINKAN",
    "MENGATUR",
    "BAGIAN_DARI",
    "TERDIRI_DARI",
    "BERGANTUNG_PADA",
    "BERINTERAKSI_DENGAN",
    "BEREAKSI_DENGAN",
    "MENGHASILKAN",
    "MEMPENGARUHI",
    "DIFORMULASIKAN_SEBAGAI",
]


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


# =============================================================================
# Per-Bab Extraction Schema (ToC-enforced with inline relations)
# =============================================================================


class KonsepRelation(BaseModel):
    """A typed relation from one konsep to another."""

    type: RelationType
    target: str  # Name of target konsep
    description: str = ""  # Brief explanation of why this relation exists


class KonsepWithRelations(BaseModel):
    """Konsep with inline relations for per-Bab extraction."""

    name: str
    description: str
    bloom_level: BloomLevel | None = None
    relations: list[KonsepRelation] = []


class SubBabExtraction(BaseModel):
    """Extraction result for one SubBab (enforced to match ToC name)."""

    name: str  # Must match SubBab name from ToC exactly
    konsep: list[KonsepWithRelations] = []


class BabExtraction(BaseModel):
    """Per-Bab LLM output schema for ToC-enforced extraction."""

    bab_summary: str = ""  # 2-3 sentence academic summary
    sub_bab: list[SubBabExtraction]
