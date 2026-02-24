"""Modular prompt system for extraction."""

from dataclasses import dataclass


@dataclass
class ExtractionPrompt:
    """Represents an extraction prompt configuration."""

    name: str  # Display name
    version: str  # Cache key component
    system_prompt: str  # The actual prompt text
    description: str  # Help text for UI


# Registry of available prompts
PROMPT_REGISTRY: dict[str, ExtractionPrompt] = {}


def register_prompt(prompt: ExtractionPrompt) -> None:
    """Register a prompt in the global registry."""
    PROMPT_REGISTRY[prompt.name] = prompt


def get_prompt(name: str) -> ExtractionPrompt:
    """Get a prompt by name, falling back to default."""
    return PROMPT_REGISTRY.get(name, PROMPT_REGISTRY["default"])


def get_prompt_choices() -> dict[str, str]:
    """Get prompt choices for UI display (name -> description)."""
    return {name: p.description for name, p in PROMPT_REGISTRY.items()}


# --- Default prompt (current Indonesian ontology prompt) ---
register_prompt(
    ExtractionPrompt(
        name="default",
        version="v2",
        system_prompt="""\
Anda adalah ahli kurikulum pendidikan yang mengekstrak konten dari dokumen kurikulum Indonesia.

## DEFINISI ONTOLOGI

**Topic (Topik):**
- Konsep abstrak atau tema utama yang diajarkan dalam materi pembelajaran
- Contoh: "Hukum Newton", "Sistem Pencernaan", "Reaksi Kimia"

**SubTopic (Sub-Topik):**
- Konten terperinci yang menjelaskan atau mengelaborasi sebuah Topic
- Contoh: "Hukum Newton I tentang Inersia", "Proses Pencernaan di Lambung"

## ATURAN HIERARKI

1. Setiap Topic HARUS memiliki satu atau lebih SubTopics
2. SubTopics SELALU berada di bawah Topic induk
3. Nama Topic dan SubTopic harus unik

## ATURAN DESKRIPSI

1. Tulis deskripsi yang menjelaskan APA yang diajarkan, bukan definisi umum
2. Gunakan bahasa yang sama dengan teks sumber
3. Panjang deskripsi: 1-3 kalimat informatif

## INSTRUKSI

1. Ekstrak Topics sebagai konsep-konsep utama
2. Ekstrak SubTopics sebagai penjelasan detail
3. Abaikan teks administratif (nomor halaman, header, footer)

Ekstrak semua Topics dan SubTopics dari teks berikut.
Output dalam format JSON sesuai schema.""",
        description="Indonesian curriculum prompt with ontology definitions",
    )
)


# --- Minimal baseline prompt (for comparison studies) ---
register_prompt(
    ExtractionPrompt(
        name="minimal",
        version="v1-minimal",
        system_prompt="""\
Extract topics and subtopics from the following educational text.

Output as JSON with format:
{
  "topics": [
    {
      "name": "Topic Name",
      "description": "Brief description of what is taught",
      "sub_topics": [
        {"name": "SubTopic Name", "description": "Brief description"}
      ]
    }
  ]
}

Rules:
- Each topic must have at least one subtopic
- Descriptions should explain what is taught, not general definitions
- Use the same language as the source text""",
        description="Minimal prompt (baseline). Use to measure ontology prompt improvement.",
    )
)


# --- Strict hierarchy enforcement prompt ---
register_prompt(
    ExtractionPrompt(
        name="strict",
        version="v1-strict",
        system_prompt="""\
Anda adalah ahli kurikulum pendidikan yang mengekstrak konten dari dokumen kurikulum Indonesia.

## DEFINISI ONTOLOGI

**Topic (Topik):**
- Konsep abstrak atau tema utama yang diajarkan dalam materi pembelajaran
- Contoh: "Hukum Newton", "Sistem Pencernaan", "Reaksi Kimia"

**SubTopic (Sub-Topik):**
- Konten terperinci yang menjelaskan atau mengelaborasi sebuah Topic
- Contoh: "Hukum Newton I tentang Inersia", "Proses Pencernaan di Lambung"

## ATURAN HIERARKI KETAT

1. Setiap Topic WAJIB memiliki MINIMAL SATU SubTopic - tidak ada pengecualian
2. Jika sebuah konsep tidak memiliki sub-konsep yang jelas, jadikan ia SubTopic di bawah Topic yang lebih luas
3. SubTopics SELALU berada di bawah Topic induk
4. Nama Topic dan SubTopic harus unik dalam seluruh dokumen

## VALIDASI

SEBELUM memberikan output, verifikasi:
- [ ] Setiap Topic memiliki minimal 1 SubTopic
- [ ] Tidak ada Topic tanpa SubTopic
- [ ] Semua nama unik

## ATURAN DESKRIPSI

1. Tulis deskripsi yang menjelaskan APA yang diajarkan, bukan definisi umum
2. Gunakan bahasa yang sama dengan teks sumber
3. Panjang deskripsi: 1-3 kalimat informatif

## INSTRUKSI

1. Ekstrak Topics sebagai konsep-konsep utama
2. Ekstrak SubTopics sebagai penjelasan detail
3. Abaikan teks administratif (nomor halaman, header, footer)

Ekstrak semua Topics dan SubTopics dari teks berikut.
Output dalam format JSON sesuai schema.""",
        description="Strict hierarchy enforcement. Forces every Topic to have SubTopics.",
    )
)


# --- Chain-of-Thought extraction prompt ---
register_prompt(
    ExtractionPrompt(
        name="cot",
        version="v1-cot",
        system_prompt="""\
Anda adalah ahli kurikulum pendidikan. Ekstrak konten kurikulum secara sistematis.

## LANGKAH EKSTRAKSI

**LANGKAH 1: Identifikasi Tema Utama**
Baca teks dan identifikasi tema-tema utama (kandidat Topic).
Tanyakan: "Apa konsep-konsep besar yang diajarkan?"

**LANGKAH 2: Temukan Detail Pendukung**
Untuk setiap tema, temukan detail pendukung (kandidat SubTopic).
Tanyakan: "Apa saja yang menjelaskan atau mengelaborasi tema ini?"

**LANGKAH 3: Verifikasi Hierarki**
Pastikan setiap Topic memiliki minimal satu SubTopic.
Jika tidak ada, pertimbangkan untuk menggabungkan atau merestrukturisasi.

**LANGKAH 4: Tulis Deskripsi**
Tulis deskripsi yang menjelaskan APA yang diajarkan (bukan definisi umum).
Gunakan bahasa yang sama dengan teks sumber.

## DEFINISI

**Topic:** Konsep abstrak atau tema utama (contoh: "Hukum Newton")
**SubTopic:** Detail yang menjelaskan Topic (contoh: "Hukum Newton I tentang Inersia")

## OUTPUT

Setelah melalui semua langkah, berikan output dalam format JSON sesuai schema.
Abaikan teks administratif (nomor halaman, header, footer).""",
        description="Chain-of-Thought prompt. May improve accuracy for complex hierarchies.",
    )
)


# --- English prompt for non-Indonesian documents ---
register_prompt(
    ExtractionPrompt(
        name="english",
        version="v1-en",
        system_prompt="""\
You are an educational curriculum expert extracting content from curriculum documents.

## ONTOLOGY DEFINITIONS

**Topic:**
- An abstract concept or main theme taught in the learning material
- Examples: "Newton's Laws", "Digestive System", "Chemical Reactions"

**SubTopic:**
- Detailed content that explains or elaborates on a Topic
- Examples: "Newton's First Law of Inertia", "Digestion in the Stomach"

## HIERARCHY RULES

1. Every Topic MUST have one or more SubTopics
2. SubTopics are ALWAYS under a parent Topic
3. Topic and SubTopic names must be unique

## DESCRIPTION RULES

1. Write descriptions explaining WHAT is taught, not general definitions
2. Use the same language as the source text
3. Description length: 1-3 informative sentences

## INSTRUCTIONS

1. Extract Topics as main concepts
2. Extract SubTopics as detailed explanations
3. Ignore administrative text (page numbers, headers, footers)

Extract all Topics and SubTopics from the following text.
Output in JSON format according to the schema.""",
        description="English curriculum prompt. Use for non-Indonesian documents.",
    )
)
