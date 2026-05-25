# extraction-v4-validated-byCC -- derivation

## What this state is

`extraction-v3-toc-gap-byCC` validated and enriched by two new expert reviews
(`expert-fisika-4` and `expert-biologi-4`), both received 2026-05-25.
All additions produced by **Claude Code (Opus 4.7)**.

## Source state

`extraction-v3-toc-gap-byCC` (v2-reviewed + 8 CC-added concepts from ToC gap analysis).

## Expert reviews integrated

### expert-biologi-4 (completed 2026-05-23)
- **151/151 triples rated "correct"** -- full validation
- 0 missing triples proposed
- 2 cosmetic comments (indices 43, 80) -- wording suggestions, no structural changes
- **Verdict:** Biology KG confirmed complete by second reviewer

### expert-fisika-4 (completed 2026-05-25)
- **239/240 triples rated "correct"**, 1 rated "missing" (index 60)
- 222 detailed comments -- physics explanations validating each triple
- **15 missing triples proposed** -- handled as follows:

| # | Proposed Triple | Action | Provenance |
|---|---|---|---|
| 1 | Muatan Kapasitor + V=E.d formulas | **NEW CONCEPT** added | expert-proposed-fisika-4 |
| 2 | Alat Ukur Listrik (Amperemeter/Voltmeter) | **NEW CONCEPT** added | expert-proposed-fisika-4 |
| 3 | Efisiensi Transformator (eta formula) | **NEW CONCEPT** added | expert-proposed-fisika-4 |
| 4 | Nilai Efektif AC (Ief, Vef formulas) | **NEW CONCEPT** added | expert-proposed-fisika-4 |
| 5 | Frekuensi Resonansi RLC formula | SKIPPED -- concept exists, formula already implicit | -- |
| 6 | Inframerah BAGIAN_DARI Spektrum | ALREADY COVERED by CC (v3) | toc-gap-completion |
| 7 | Inframerah remote+terapi | **NEW RELATION** added to Pemanfaatan Inframerah | expert-proposed-fisika-4 |
| 8 | Gerbang XOR | **NEW RELATION** added to Gerbang Logika Dasar | expert-proposed-fisika-4 |
| 9 | Transformasi Galileo | **NEW RELATION** added to Gerak Relatif Newton | expert-proposed-fisika-4 |
| 10 | Dilatasi Waktu formula | ALREADY COVERED by CC (v3) | toc-gap-completion |
| 11 | Penambahan Kecepatan formula | ALREADY COVERED by CC (v3) | toc-gap-completion |
| 12 | Sinar-X lambda_min formula | **NEW RELATION** added to Pembangkitan Sinar-X | expert-proposed-fisika-4 |
| 13 | Dualisme Gelombang-Partikel | **NEW CONCEPT** added | expert-proposed-fisika-4 |
| 14 | Peluruhan Nt formula | **NEW RELATION** added to Peluruhan (radioaktif) | expert-proposed-fisika-4 |
| 15 | Defek Massa Delta_m formula | **NEW RELATION** added to Defek Massa | expert-proposed-fisika-4 |

### CC additions independently validated by expert

3 of the 5 CC-added concepts from v3 were independently proposed by expert-fisika-4:
- **Pemanfaatan Inframerah** (expert proposed items 6-7)
- **Dilatasi Waktu** (expert proposed item 10)
- **Penambahan Kecepatan Relativistik** (expert proposed item 11)

This provides strong external confirmation that the ToC-gap methodology identified real gaps.

## What changed in v4 (Fisika only)

| Change Type | Count | Provenance |
|---|---|---|
| New concepts | 5 | expert-proposed-fisika-4 |
| New relations on existing concepts | 6 | expert-proposed-fisika-4 |
| **Total new triples** | **16** | |

Concepts added:
1. **Muatan Kapasitor dan Beda Potensial Pelat Paralel** (LISTRIK STATIS / C. Kapasitor)
2. **Alat Ukur Listrik** (LISTRIK ARUS SEARAH / D. Rangkaian Listrik)
3. **Efisiensi Transformator** (KEMAGNETAN / G. Induktansi dan Transformator)
4. **Nilai Efektif Arus dan Tegangan AC** (ARUS BOLAK-BALIK / A. Persamaan AC)
5. **Dualisme Gelombang-Partikel** (GEJALA KUANTUM / B. Efek Fotolistrik)

Relations added to existing concepts:
- Gerbang Logika Dasar -> TERDIRI_DARI -> Gerbang XOR
- Gerak Relatif Newton -> MENGGUNAKAN -> Transformasi Galileo
- Pembangkitan Sinar-X -> DIFORMULASIKAN_SEBAGAI -> lambda_min = hc/eV
- Peluruhan (radioaktif) -> DIFORMULASIKAN_SEBAGAI -> Nt = N0.(1/2)^(t/t1/2)
- Defek Massa -> DIFORMULASIKAN_SEBAGAI -> Delta_m = (Z.mp+(A-Z).mn)-m_inti
- Pemanfaatan Inframerah -> MEMUNGKINKAN -> Terapi Fisik Medis

## Per-grade summary (v4)

| Grade | Original | CC added (v3) | Expert-4 added (v4) | Total concepts |
|---|---:|---:|---:|---:|
| Biologi Kelas XII | 80 | 0 | 0 | 80 |
| Fisika Kelas XII | 124 | 5 | 5 | 134 |
| Kimia Kelas XII | 141 | 3 | 0 | 144 |
| **Total** | **345** | **8** | **5** | **358** |

## How to filter by provenance

```python
import json
data = json.load(open("Fisika Kelas XII.json", encoding="utf-8"))
for ch in data["chapters"]:
    for st in ch["subtopics"]:
        for c in st["concepts"]:
            prov = c.get("provenance", "extraction")
            # "extraction" = original pipeline
            # "toc-gap-completion" = CC ToC-gap additions (v3)
            # "expert-proposed-fisika-4" = expert review additions (v4)
            # "expert-proposed" = expert-kimia-6 additions (v2)
```

## Reproducibility

```bash
python experiments/scripts/add_expert4_missing_triples.py
```

Script is idempotent (checks for existing concepts/relation targets before adding).

## Attribution

- v3 ToC-gap additions: Claude Code (Opus 4.7)
- v4 expert-proposed additions: expert-fisika-4 (reviewer), integrated by Claude Code
- Expert descriptions used directly as concept descriptions (sufficiently detailed, 18-57 words each with formulas)
