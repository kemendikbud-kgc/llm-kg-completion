# extraction-v3-toc-gap-byCC -- derivation

## What this state is

`extraction-v2-reviewed` enriched with **8 missing concepts** identified by
comparing book PDF tables of contents against the reviewed KG. All additions
were produced by **Claude Code (Opus 4.7)** on 2026-05-25.

## Source state

`extraction-v2-reviewed` (the expert-reviewed baseline from 2026-05-13).

## How it was produced

### Methodology: ToC-targeted gap analysis (not full-sweep)

1. **Loaded** all concept names from the 3 reviewed KG JSONs (Bio: 80, Fisika: 131, Kimia: 199 concepts).
2. **Extracted** book Tables of Contents from the Kelas XII PDFs:
   - Fisika & Kimia: read directly from PDF (image-based ToC pages)
   - Biologi: extracted via pymupdf script (PDF exceeds 100MB tool limit)
3. **Compared** every ToC section (Bab / SubBab / sub-subsection) against existing KG concept names to find sections with no matching concept.
4. **Read the specific book pages** for each confirmed gap to extract accurate Indonesian descriptions from the actual textbook prose.
5. **Constructed** concept entries matching the existing JSON schema, with `provenance: "toc-gap-completion"` and `n_reviewers: 0`.
6. **Inserted** via idempotent Python script (`experiments/scripts/add_toc_gap_concepts.py`).

### What was NOT done

- Full-sweep page-by-page reading (only ToC + gap pages were read)
- Depth analysis within already-covered subtopics (e.g., if a subtopic has 5 concepts in the KG but the book discusses 10, this scan would not detect the missing 5)
- Any modification to existing concepts or relations

## What Claude Code added

### Fisika Kelas XII (+5 concepts, +9 relations)

| # | Concept | Subtopic | Book Page | Relations |
|---|---------|----------|-----------|-----------|
| 1 | **Pemanfaatan Inframerah** | D. Pemanfaatan Gelombang Elektromagnetik (BAB 5) | p.107 | BAGIAN_DARI Spektrum Elektromagnetik; MEMUNGKINKAN Pengukuran Suhu Non-Kontak |
| 2 | **Gerak Relatif Newton** | A. Postulat Pertama dan Kedua Einstein (BAB 7) | p.136 | MEMPERSIAPKAN Postulat Relativitas Khusus Einstein |
| 3 | **Dilatasi Waktu** | B. Dampak Relativitas Einstein (BAB 7) | p.142 | BERGANTUNG_PADA Faktor Lorentz (g); DIFORMULASIKAN_SEBAGAI t = t0/sqrt(1-v^2/c^2) |
| 4 | **Penambahan Kecepatan Relativistik** | B. Dampak Relativitas Einstein (BAB 7) | p.146 | BERGANTUNG_PADA Transformasi Lorentz; DIFORMULASIKAN_SEBAGAI V = (v1+v2)/(1+v1v2/c^2) |
| 5 | **Pengerutan Panjang** | B. Dampak Relativitas Einstein (BAB 7) | p.148 | BERGANTUNG_PADA Faktor Lorentz (g); DIFORMULASIKAN_SEBAGAI L = L0*sqrt(1-v^2/c^2) |

**Why these were missing:** Concepts 3-5 were bundled into a single generic concept
"Dampak Relativitas Einstein berdasarkan Transformasi Lorentz" in v1/v2. The book
has dedicated sub-sections (B.1, B.2, B.3) with separate formulas for each.
Concept 2 was referenced as a dangling target in `chapter_relations` but never
defined as an actual concept. Concept 1 was the only spectrum member in section D
without a dedicated "Pemanfaatan" concept (UV, Gamma/X, Mikro, Radio all had one).

### Kimia Kelas XII (+3 concepts, +6 relations)

| # | Concept | Subtopic | Book Page | Relations |
|---|---------|----------|-----------|-----------|
| 1 | **Stoikiometri Larutan** | C. Kesetimbangan dalam Larutan (Bab I) | p.27 | MENGHASILKAN Reaksi Pengendapan; BERGANTUNG_PADA Titrasi Asam Basa |
| 2 | **Perbandingan Sel Volta dan Sel Elektrolisis** | C. Sel elektrokimia (Bab II) | p.87 | TERDIRI_DARI Sel Volta; TERDIRI_DARI Sel Elektrolisis |
| 3 | **Mobil Listrik** | E. Aplikasi elektrokimia (Bab II) | p.101 | MENGGUNAKAN Baterai Litium-ion; BAGIAN_DARI Reaksi Elektrokimia |

**Why these were missing:** All three are sub-subsections in the book ToC that had
zero concept matches in the v2-reviewed KG (confirmed via grep).

### Biologi Kelas XII (+0)

All 4 chapters and their SubBabs (A-H) in the book ToC match existing KG
subtopics. No structural gaps at the ToC level.

## Annotation schema for new concepts

New concepts use a distinct provenance value and empty review block:

```json
{
  "name": "Dilatasi Waktu",
  "description": "...",
  "glossary_validated": false,
  "materi_pokok_ref": "Transformasi Lorentz",
  "provenance": "toc-gap-completion",
  "relations": [
    {
      "type": "BERGANTUNG_PADA",
      "target": "Faktor Lorentz (g)",
      "description": "...",
      "provenance": "toc-gap-completion",
      "expert_review": {
        "status": "proposed",
        "consensus": "proposed",
        "n_reviewers": 0,
        "ratings": {},
        "comments": {}
      }
    }
  ]
}
```

This distinguishes them from:
- Original extraction (no `provenance` field)
- Expert-proposed triples (`provenance: "expert-proposed"`, `n_reviewers: 1`)
- ToC-gap additions (`provenance: "toc-gap-completion"`, `n_reviewers: 0`)

## Per-grade summary

| Grade | v2-reviewed triples | CC added concepts | CC added relations | v3 total concepts |
|---|---:|---:|---:|---:|
| Biologi Kelas XII | 151 kept + 0 proposed | 0 | 0 | 80 |
| Fisika Kelas XII | 237 kept + 0 proposed | **5** | **9** | 134 |
| Kimia Kelas XII | 164 kept + 29 proposed | **3** | **6** | 202 |
| **Total** | 552 + 29 = 581 | **8** | **15** | **416** |

## Reproducibility

```bash
python experiments/scripts/add_toc_gap_concepts.py
```

The script is idempotent -- re-running skips concepts that already exist (by name match).

## How to filter CC additions

To find only Claude Code's additions in any JSON:

```python
import json
data = json.load(open("Fisika Kelas XII.json", encoding="utf-8"))
cc_concepts = [
    c for ch in data["chapters"]
    for st in ch["subtopics"]
    for c in st["concepts"]
    if c.get("provenance") == "toc-gap-completion"
]
```

## Attribution

All 8 concepts were extracted and authored by Claude Code (Opus 4.7, 1M context).
Descriptions are sourced from the Kurikulum Merdeka textbook PDFs, not generated
from model knowledge. Relation types follow the existing KG conventions
(SCREAMING_SNAKE_CASE, matching attested types in the v2-reviewed data).
