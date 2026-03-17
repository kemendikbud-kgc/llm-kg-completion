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


# =============================================================================
# ToC-Enforced Per-Bab Prompt Builder
# =============================================================================

TOC_BAB_PROMPT_TEMPLATE = """\
Anda sedang membangun knowledge graph akademis dari buku teks Indonesia.

## KONTEKS BAB

**Bab Saat Ini:** "{bab_name}"

## STRUKTUR SUBCHAPTER (DARI DAFTAR ISI)

Bab ini memiliki subchapter berikut sesuai struktur buku:
{subbab_list}

**PENTING:**
- Gunakan nama subchapter di atas sebagai field "name" dalam array "sub_bab"
- Jangan membuat nama subchapter sendiri — ikuti struktur buku secara persis
- Setiap subchapter WAJIB memiliki minimal 1 konsep
- Jika konten spesifik tidak tersedia dalam teks, buat 1 konsep ringkasan berdasarkan nama subchapter

## DEFINISI KONSEP

**Konsep:**
- Konsep abstrak atau tema utama yang diajarkan dalam materi pembelajaran
- Contoh: "Hukum Newton", "Sistem Pencernaan", "Laju Reaksi"

**Deskripsi:**
- Jelaskan APA yang diajarkan, bukan definisi umum
- Panjang: 1-3 kalimat informatif
- Gunakan bahasa Indonesia

## TINGKATAN BLOOM (bloom_level)

Tentukan tingkat kognitif untuk setiap konsep:
- **remember**: menghafal, menyebutkan, mendefinisikan
- **understand**: menjelaskan, mengidentifikasi, merangkum
- **apply**: menerapkan, menghitung, menggunakan
- **analyze**: menganalisis, membandingkan, menguraikan
- **evaluate**: mengevaluasi, menilai, mengkritisi
- **create**: merancang, membuat, menghasilkan

## TIPE RELASI

Untuk setiap konsep, identifikasi relasi ke konsep LAIN dalam bab ini.
Pilih tipe relasi yang paling tepat:

- **MENDEFINISIKAN**: konsep sumber memberikan definisi untuk target
- **MENYEBABKAN**: konsep sumber menyebabkan atau menghasilkan target
- **MEMUNGKINKAN**: konsep sumber memungkinkan terjadinya target
- **MENGATUR**: konsep sumber mengatur atau mengontrol target
- **BAGIAN_DARI**: konsep sumber adalah bagian dari target
- **TERDIRI_DARI**: konsep sumber terdiri dari atau mencakup target
- **BERGANTUNG_PADA**: konsep sumber bergantung pada target
- **BERINTERAKSI_DENGAN**: konsep sumber berinteraksi dengan target
- **BEREAKSI_DENGAN**: konsep sumber bereaksi secara kimia dengan target
- **MENGHASILKAN**: konsep sumber menghasilkan atau memproduksi target
- **MEMPENGARUHI**: konsep sumber mempengaruhi target
- **DIFORMULASIKAN_SEBAGAI**: konsep sumber diformulasikan dalam rumus target

## ATURAN RELASI

1. Relasi bersifat OPSIONAL — tidak semua konsep memiliki relasi
2. Target relasi adalah nama konsep LAIN dalam bab ini
3. Deskripsi relasi: 1 kalimat singkat menjelaskan MENGAPA relasi ini ada
4. Maksimal 3 relasi per konsep

## FILTER KONTEN

Abaikan sepenuhnya:
- Daftar isi, nomor halaman, judul buku, nama penulis
- Informasi penerbit, header/footer
- Instruksi soal, pertanyaan latihan
- Keterangan gambar, rangkuman, glosarium, indeks

Ekstrak HANYA pengetahuan ilmiah yang bermakna dari isi buku.

## TARGET JUMLAH

- Maksimal 3-5 konsep per subchapter
- Lebih sedikit tapi akurat lebih baik
{glossary_section}
## FORMAT OUTPUT (JSON)

{{
  "bab_summary": "Ringkasan akademis bab ini (2-3 kalimat)",
  "sub_bab": [
    {{
      "name": "Nama subchapter sesuai daftar di atas",
      "konsep": [
        {{
          "name": "Nama Konsep",
          "description": "Deskripsi 1-3 kalimat",
          "bloom_level": "understand",
          "relations": [
            {{
              "type": "MENYEBABKAN",
              "target": "Nama Konsep Target",
              "description": "Penjelasan singkat mengapa relasi ini ada"
            }}
          ]
        }}
      ]
    }}
  ]
}}

CATATAN:
- "relations" bersifat opsional — kosongkan array jika tidak ada relasi yang relevan
- Setiap sub_bab WAJIB memiliki minimal 1 konsep

Teks Bab:
{text_chunk}"""


def build_toc_bab_system_prompt(
    bab_name: str,
    subbab_names: list[str],
    glossary: dict[str, str] | None = None,
) -> str:
    """Build the per-Bab ToC-enforced system prompt.

    Args:
        bab_name: Name of the current Bab (chapter)
        subbab_names: List of SubBab names from the ToC (exact names to enforce)
        glossary: Optional glossary dict for terminology validation

    Returns:
        Complete system prompt string ready for LLM call
    """
    # Build SubBab list
    subbab_list = "\n".join(f"  {i + 1}. {name}" for i, name in enumerate(subbab_names))

    # Build glossary section if provided
    if glossary:
        glossary_section = build_glossary_context(glossary)
    else:
        glossary_section = ""

    return TOC_BAB_PROMPT_TEMPLATE.format(
        bab_name=bab_name,
        subbab_list=subbab_list,
        glossary_section=glossary_section,
        text_chunk="{text_chunk}",  # Placeholder for later substitution
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


# --- ToC-Enforced Per-Bab prompt (uses build_toc_bab_system_prompt) ---
# Note: This is a placeholder; actual prompt is built dynamically with ToC structure
register_prompt(
    ExtractionPrompt(
        name="toc_bab",
        version="v4-toc-bab",
        system_prompt=TOC_BAB_PROMPT_TEMPLATE,  # Template, will be customized per-Bab
        description="ToC-enforced per-Bab extraction with inline relations. Best for structured textbooks.",
    )
)
