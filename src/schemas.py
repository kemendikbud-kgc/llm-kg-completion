"""Pydantic models for structured LLM extraction."""

from pydantic import BaseModel


class SubTopic(BaseModel):
    name: str
    description: str


class Topic(BaseModel):
    name: str
    description: str
    sub_topics: list[SubTopic] = []


class Subject(BaseModel):
    """Indonesian curriculum subject (Mata Pelajaran)."""

    name: str  # e.g., "Fisika", "Biologi", "Kimia"
    phase: str = ""  # "E" (Kelas X) or "F" (Kelas XI-XII)


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


class TopicExtraction(BaseModel):
    subject: Subject | None = None  # Auto-detected or user-selected
    topics: list[Topic]
