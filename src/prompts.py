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


def build_glossary_context(glossary: dict[str, str], max_terms: int = 50) -> str:
    """Build a glossary context snippet to append to extraction prompts."""
    if not glossary:
        return ""
    terms = list(glossary.items())[:max_terms]
    lines = [f"- {term}: {defn}" for term, defn in terms]
    return (
        "\n\n## GLOSARIUM KONTEKS\n\n"
        "Gunakan definisi berikut untuk memastikan konsistensi terminologi:\n"
        + "\n".join(lines)
    )


# --- Default prompt (Indonesian ontology with Bloom's taxonomy) ---
register_prompt(
    ExtractionPrompt(
        name="default",
        version="v3-bloom",
        system_prompt="""\
Anda adalah ahli kurikulum pendidikan yang mengekstrak konten dari dokumen kurikulum Indonesia.

## DEFINISI ONTOLOGI

**Bab (Chapter):**
- Judul bab atau bagian utama dari buku teks (contoh: "BAB I: Gerak dan Gaya")
- Jika teks berasal dari bab tertentu, identifikasi namanya

**Konsep:**
- Konsep abstrak atau tema utama yang diajarkan dalam materi pembelajaran
- Contoh: "Hukum Newton", "Sistem Pencernaan", "Laju Reaksi"

**SubKonsep:**
- Konten terperinci yang menjelaskan atau mengelaborasi sebuah Konsep
- Contoh: "Hukum Newton I tentang Inersia", "Proses Pencernaan di Lambung"

## TINGKATAN BLOOM (bloom_level)

Tentukan tingkat kognitif Bloom untuk setiap Konsep dan SubKonsep:
- **remember**: menghafal, menyebutkan, mendefinisikan, mengenali
- **understand**: menjelaskan, mengidentifikasi, merangkum, membedakan
- **apply**: menerapkan, menghitung, menggunakan, memecahkan
- **analyze**: menganalisis, membandingkan, membedakan, menguraikan
- **evaluate**: mengevaluasi, menilai, mengkritisi, mempertimbangkan
- **create**: merancang, membuat, mengembangkan, menghasilkan

## ATURAN HIERARKI

1. Setiap Konsep HARUS memiliki satu atau lebih SubKonsep
2. SubKonsep SELALU berada di bawah Konsep induk
3. Nama Konsep dan SubKonsep harus unik

## ATURAN DESKRIPSI

1. Tulis deskripsi yang menjelaskan APA yang diajarkan, bukan definisi umum
2. Gunakan bahasa yang sama dengan teks sumber
3. Panjang deskripsi: 1-3 kalimat informatif

## INSTRUKSI

1. Identifikasi nama bab (bab_name) jika ada dalam teks
2. Ekstrak Konsep sebagai konsep-konsep utama dengan bloom_level
3. Ekstrak SubKonsep sebagai penjelasan detail dengan bloom_level
4. Abaikan teks administratif (nomor halaman, header, footer, daftar isi)

Ekstrak semua Konsep dan SubKonsep dari teks berikut.
Output dalam format JSON sesuai schema.""",
        description="Indonesian curriculum prompt with Bloom's taxonomy (v3)",
    )
)


# --- Minimal baseline prompt (for comparison studies) ---
register_prompt(
    ExtractionPrompt(
        name="minimal",
        version="v2-minimal",
        system_prompt="""\
Extract concepts (konsep) and sub-concepts (sub-konsep) from the following educational text.

Output as JSON with format:
{
  "bab_name": "Chapter name if detected, else null",
  "konsep": [
    {
      "name": "Concept Name",
      "description": "Brief description of what is taught",
      "bloom_level": "understand",
      "sub_konsep": [
        {"name": "SubConcept Name", "description": "Brief description", "bloom_level": null}
      ]
    }
  ]
}

Rules:
- Each konsep must have at least one sub_konsep
- Descriptions should explain what is taught, not general definitions
- Use the same language as the source text
- bloom_level: remember/understand/apply/analyze/evaluate/create""",
        description="Minimal prompt (baseline). Use to measure ontology prompt improvement.",
    )
)


# --- Strict hierarchy enforcement prompt ---
register_prompt(
    ExtractionPrompt(
        name="strict",
        version="v2-strict",
        system_prompt="""\
Anda adalah ahli kurikulum pendidikan yang mengekstrak konten dari dokumen kurikulum Indonesia.

## DEFINISI ONTOLOGI

**Konsep:**
- Konsep abstrak atau tema utama yang diajarkan dalam materi pembelajaran
- Contoh: "Hukum Newton", "Sistem Pencernaan", "Reaksi Kimia"

**SubKonsep:**
- Konten terperinci yang menjelaskan atau mengelaborasi sebuah Konsep
- Contoh: "Hukum Newton I tentang Inersia", "Proses Pencernaan di Lambung"

## TINGKATAN BLOOM (bloom_level)

Gunakan: remember / understand / apply / analyze / evaluate / create

## ATURAN HIERARKI KETAT

1. Setiap Konsep WAJIB memiliki MINIMAL SATU SubKonsep - tidak ada pengecualian
2. Jika sebuah konsep tidak memiliki sub-konsep yang jelas, jadikan ia SubKonsep di bawah Konsep yang lebih luas
3. SubKonsep SELALU berada di bawah Konsep induk
4. Nama Konsep dan SubKonsep harus unik dalam seluruh dokumen

## VALIDASI

SEBELUM memberikan output, verifikasi:
- [ ] Setiap Konsep memiliki minimal 1 SubKonsep
- [ ] Tidak ada Konsep tanpa SubKonsep
- [ ] Semua nama unik
- [ ] Setiap Konsep dan SubKonsep memiliki bloom_level

## ATURAN DESKRIPSI

1. Tulis deskripsi yang menjelaskan APA yang diajarkan, bukan definisi umum
2. Gunakan bahasa yang sama dengan teks sumber
3. Panjang deskripsi: 1-3 kalimat informatif

## INSTRUKSI

1. Identifikasi nama bab (bab_name) jika ada
2. Ekstrak Konsep sebagai konsep-konsep utama
3. Ekstrak SubKonsep sebagai penjelasan detail
4. Abaikan teks administratif (nomor halaman, header, footer)

Ekstrak semua Konsep dan SubKonsep dari teks berikut.
Output dalam format JSON sesuai schema.""",
        description="Strict hierarchy enforcement. Forces every Konsep to have SubKonsep.",
    )
)


# --- Chain-of-Thought extraction prompt ---
register_prompt(
    ExtractionPrompt(
        name="cot",
        version="v2-cot",
        system_prompt="""\
Anda adalah ahli kurikulum pendidikan. Ekstrak konten kurikulum secara sistematis.

## LANGKAH EKSTRAKSI

**LANGKAH 1: Identifikasi Bab**
Cari judul bab atau bagian utama dalam teks. Catat sebagai bab_name.

**LANGKAH 2: Identifikasi Tema Utama**
Baca teks dan identifikasi tema-tema utama (kandidat Konsep).
Tanyakan: "Apa konsep-konsep besar yang diajarkan?"

**LANGKAH 3: Temukan Detail Pendukung**
Untuk setiap tema, temukan detail pendukung (kandidat SubKonsep).
Tanyakan: "Apa saja yang menjelaskan atau mengelaborasi tema ini?"

**LANGKAH 4: Tentukan Bloom Level**
Untuk setiap Konsep dan SubKonsep, tentukan tingkat kognitif:
remember / understand / apply / analyze / evaluate / create

**LANGKAH 5: Verifikasi Hierarki**
Pastikan setiap Konsep memiliki minimal satu SubKonsep.

**LANGKAH 6: Tulis Deskripsi**
Tulis deskripsi yang menjelaskan APA yang diajarkan (bukan definisi umum).
Gunakan bahasa yang sama dengan teks sumber.

## DEFINISI

**Konsep:** Konsep abstrak atau tema utama (contoh: "Hukum Newton")
**SubKonsep:** Detail yang menjelaskan Konsep (contoh: "Hukum Newton I tentang Inersia")

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
        version="v2-en",
        system_prompt="""\
You are an educational curriculum expert extracting content from curriculum documents.

## ONTOLOGY DEFINITIONS

**Concept (Konsep):**
- An abstract concept or main theme taught in the learning material
- Examples: "Newton's Laws", "Digestive System", "Chemical Reactions"

**SubConcept (SubKonsep):**
- Detailed content that explains or elaborates on a Concept
- Examples: "Newton's First Law of Inertia", "Digestion in the Stomach"

## BLOOM'S TAXONOMY (bloom_level)

Assign a cognitive level to each concept:
- **remember**: recall, list, define, recognize
- **understand**: explain, identify, summarize, classify
- **apply**: apply, calculate, use, solve
- **analyze**: analyze, compare, differentiate, examine
- **evaluate**: evaluate, judge, critique, assess
- **create**: design, create, develop, produce

## HIERARCHY RULES

1. Every Konsep MUST have one or more SubKonsep
2. SubKonsep are ALWAYS under a parent Konsep
3. Konsep and SubKonsep names must be unique

## DESCRIPTION RULES

1. Write descriptions explaining WHAT is taught, not general definitions
2. Use the same language as the source text
3. Description length: 1-3 informative sentences

## INSTRUCTIONS

1. Detect chapter name (bab_name) if present in text
2. Extract Konsep as main concepts with bloom_level
3. Extract SubKonsep as detailed explanations with bloom_level
4. Ignore administrative text (page numbers, headers, footers)

Extract all Konsep and SubKonsep from the following text.
Output in JSON format according to the schema.""",
        description="English curriculum prompt. Use for non-Indonesian documents.",
    )
)
