# Cross-Book Completion Survey — Analysis

**Step 2 (completion / LINTAS_BUKU) expert validation.** Pilot run.

| | |
|---|---|
| Source | Redis key `kg:completion-survey:dummy-user-1` (Upstash) |
| Rater | `dummy-user-1` (single rater, pilot/self-review) |
| Rated | 100 of 117 relations (unanswered: LB101–LB117) |
| Last updated | 2026-06-01T16:14:10.869Z |
| **Completion params** | **threshold = 0.7, top_k = 20 — LOOSE, pre-sweep** (high-quality target is ~0.75–0.80 / top_k 10–15, not yet swept) |
| Raw export | `lintas_buku_survey_responses.csv` (100 filled rows) |
| Reproduce | `python -m src.kg_review_redis` + key above; numbers computed ad-hoc from `data/completion_survey/lintas_buku_survey.csv` |

## Headline results

| Axis | Result | Rate |
|---|---|--:|
| 1. Relasi valid? (Ya/Tidak) | 99 Ya / 1 Tidak | **99%** |
| 2. Tipe relasi benar? (Benar/Salah) | 98 Benar / 2 Salah | **98%** |
| 3. Arah benar? (Benar/Terbalik/NA) | 74 Benar / 25 Terbalik / 1 NA | **74%** |

**The completion step reliably finds a real cross-book link (99%) and labels it correctly (98%), but gets the direction wrong 1 in 4 times. Direction is the dominant error mode.**

## Breakdown by relation type

| Relation type | n | valid | type OK | dir OK | reversed | dir % |
|---|--:|--:|--:|--:|--:|--:|
| PRASYARAT_UNTUK | 49 | 49 | 47 | 38 | 11 | 78% |
| MEMPERDALAM | 25 | 25 | 25 | 14 | 10 | **56%** |
| APLIKASI_DARI | 14 | 13 | 14 | 10 | 4 | 71% |
| BERKAITAN_DENGAN | 11 | 11 | 11 | 11 | 0 | 100% |
| SAMA_DENGAN | 1 | 1 | 1 | 1 | 0 | 100% |

- **MEMPERDALAM is weakest (56%)** — inherently directional ("A deepens understanding of B"); the model flips the arrow half the time.
- **Symmetric types are perfect** — BERKAITAN_DENGAN / SAMA_DENGAN are 100% because direction barely matters.

## Breakdown by subject pair

| Pair | n | dir OK | reversed | dir % |
|---|--:|--:|--:|--:|
| Biologi ↔ Kimia | 79 | 55 | 23 | 70% |
| Fisika ↔ Kimia | 18 | 16 | 2 | 89% |
| Biologi ↔ Fisika | 3 | 3 | 0 | 100% |

## The directional bias (key finding)

Reversed edges by **source** (konsep_A) discipline: **Biologi = 22, Fisika = 2, Kimia = 1.**

When the model makes Biology the source, it is wrong 22 times. The correct foundational direction is almost always **Kimia → Biologi** — the chemistry fundamental is the prerequisite/base, and the biology process is what *requires* or *deepens* it. The model keeps emitting `(bio process) → (chem concept)`.

### The 25 reversed edges
LB004, LB015, LB020, LB033, LB036, LB040, LB041, LB046, LB051, LB053, LB057, LB058, LB062, LB063, LB064, LB066, LB067, LB071, LB072, LB073, LB079, LB083, LB086, LB090, LB096

### The 1 invalid + 2 wrong-type
- **LB005** (invalid): Potensial Elektrode —APLIKASI_DARI→ muatan kapasitor keping sejajar… — *"lebih tepatnya potensial listrik saja, medan listrik diganti Gaya Gerak Listrik."*
- **LB008 / LB074** (wrong type): `alat ukur listrik —PRASYARAT_UNTUK→ ggl sel / sel elektrokimia` — *"bukan prasyarat, sebagai alat saja"* / *"hapus kata 'memahami' supaya tidak misleading."*

## Interpretation (mind the 0.7/20 params)

1. **Existence & typing are at ceiling even at the loose threshold.** At threshold 0.7 you would expect noise pairs to leak in, but only 1/100 was judged unrelated. Tightening to 0.75–0.80 mostly trims *recall/volume*, not precision-of-existence — there is almost nothing to clean up on the existence axis.

2. **Direction is a prompt problem, not a threshold problem.** Reversed edges are valid, high-similarity pairs pointing the wrong way; the parameter sweep will **not** remove them. This axis is orthogonal to the sweep.

3. **The fix is cheap and deterministic.** Since 22/25 errors follow one rule, a post-hoc canonicalizer that orients **Kimia → Biologi** for PRASYARAT_UNTUK and MEMPERDALAM would lift direction accuracy from 74% to ~96% on this sample. Alternative: add an explicit direction rule/example to the completion prompt.

## Caveats

- **Single rater** (`dummy-user-1`), pilot — not an expert panel. Treat as a first-pass validation.
- **100/117** rated; LB101–LB117 unanswered.
- **Un-swept config** (0.7/20). The clean thesis narrative: this pilot *isolated direction as the dominant error mode* before the parameter sweep.

## Next steps

- [ ] Cross-check the 25 reversed against yhoga's 125 LINTAS_BUKU edges → flip direction in-DB.
- [ ] Re-run survey after the parameter sweep (0.75–0.80 / 10–15) and/or with additional raters.
- [ ] Implement the Kimia→Biologi canonicalizer for PRASYARAT_UNTUK / MEMPERDALAM.
