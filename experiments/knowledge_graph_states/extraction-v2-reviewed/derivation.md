# extraction-v2-reviewed — derivation

## What this state is

The **team's shared canonical pre-completion baseline** — `extraction-v1`
enriched with expert reviewer feedback. This is the canonical KG that downstream
completion experiments (yours, your friend's, future teammates') should run against.

## Source state

`extraction-v1` + expert feedback from Redis snapshot
`data/expert_feedback/redis_snapshot_2026-05-13/`.

## How it was produced

1. Start from `extraction-v1/{Biologi,Fisika,Kimia} Kelas XII.json` — canonical
   per-Bab extraction from Yhoga's pipeline.
2. Pull `kg:courses` + every substantive reviewer's progress from Upstash via
   `experiments/redis_dump.py` → save to `data/expert_feedback/redis_snapshot_<date>/`.
3. Resolve each reviewer's numeric triple index back to a concrete triple via
   `experiments/resolve_expert_feedback.py` (the extraction-v1 JSONs and
   `kg:courses` have identical triple counts and order, so the index mapping is
   canonical).
4. Apply feedback per `experiments/build_extraction_v2_reviewed.py`:
   - `consensus = correct` → keep, annotate with `expert_review`
   - `consensus = partial` → keep, annotate with `expert_review.status = 'partial'`
   - `consensus = missing` (kurang konteks) → keep, annotate with `status = 'missing'`
   - `consensus = wrong` → **drop** (5 total). Single-reviewer drops are honored.
   - `comments` → annotation only, never override rating
   - `missingTriples` (29) → append per chapter under synthetic
     `"Expert Proposed Triples"` subtopic, with `provenance: "expert-proposed"`
     on both the concept and each relation

## Annotation schema (new in extraction-v2-reviewed)

Each kept relation may carry an `expert_review` block:

```json
{
  "type": "MENGATUR",
  "target": "Kecepatan Reaksi Kimia",
  "description": "...",
  "expert_review": {
    "status": "correct",
    "consensus": "correct",
    "n_reviewers": 2,
    "ratings": {"expert-kimia-6": "correct", "expert-fisika-2": "correct"},
    "comments": {"expert-kimia-6": "pH didefinisikan berdasarkan aktivitas..."}
  }
}
```

Expert-proposed triples additionally carry `provenance: "expert-proposed"` on
the relation. Their parent concept is grouped under a synthetic subtopic
`"Expert Proposed Triples"` so they're visually obvious in the JSON.

## Per-grade summary

| Grade | Triples in v1 | Kept | Dropped | Added | annot=correct | annot=partial | annot=needs-context |
|---|---:|---:|---:|---:|---:|---:|---:|
| Biologi Kelas XII | 151 | 151 | 0 | 0 | 147 | 3 | 1 |
| Fisika Kelas XII | 240 | 237 | 3 | 0 | 186 | 40 | 11 |
| Kimia Kelas XII | 166 | 164 | 2 | **29** | 140 | 5 | 19 |
| **Total** | **557** | **552** | **5** | **29** | **473** | **48** | **31** |

`extraction-v2-reviewed` total triples: 552 (kept) + 29 (proposed) = **581** relations.

## What got dropped

Five triples were dropped per `consensus = wrong`. Full audit at
`dropped_triples.json`. Single-reviewer drops are honored because:

- For Fisika and Kimia the rating reviewer was the only domain expert who looked
  at that course, so deferring to "the expert" is the cheapest correct policy.
- Each drop preserves the reviewer's identity, the original triple, and any
  comment text for review/override by the team.

To override a drop, edit `dropped_triples.json` (move it back manually) and
re-run `build_extraction_v2_reviewed.py` after adjusting the consensus policy.

## What got proposed (added)

29 reviewer-proposed missing triples, all from `expert-kimia-6` on the Kimia
course. Distribution by chapter:

- LARUTAN DAN KOLOID: 6
- ELEKTROKIMIA: 9
- MAKROMOLEKUL ORGANIK: 7
- GUGUS FUNGSI DALAM SENYAWA KARBON: 7

These reveal systematic under-extraction by Yhoga's pipeline, particularly
around quantitative laws (Nernst, Faraday) and structural concepts
(monomer/polymer chain, vulkanisasi, ikatan silang).

## General feedback (non-structural, for the record)

> **expert-fisika-6** (fisika-kelas-xii):
> *"Penjelasannya dipastikan jangan ada bias, ada beberapa komen juga dari saya
> di sana. Lebih ke penulisan, notasi, dan definisi nya perlu dicek dan
> dirapihkan kembali biar tidak menimbulkan bias/miss dalam penjelasannya"*

→ Action: review the 40 `partial`-rated Fisika triples + 13 comments and tighten
descriptions/notations before completion experiments. Tracked separately; does
not affect extraction-v2-reviewed structure.

## Comments worth elevating to description fixes (NOT applied to extraction-v2-reviewed)

Per the build policy, comments are annotation-only. But three kimia-6 comments
identify factual errors worth fixing in description text downstream:

| Triple | Issue | Comment |
|---|---|---|
| pH (idx 4, Kimia) | Definition uses *concentration* but should use *activity* (γ=1 hidden assumption) | "pH didefinisikan berdasarkan aktivitas ion hidrogen" |
| Termoset (idx 139, Kimia) | System claim is wrong | "termoset tidak dapat dilelehkan kembali" |
| Etanol (idx 110, Kimia) | Confusing agent | "fermentasi oleh ragi (Saccharomyces cerevisiae), bukan bakteri" |

The pelapisan/electroplating (idx 74) and etanol fermentasi (idx 110) cases
were severe enough that the reviewer rated them `wrong` — those are already
dropped, see `dropped_triples.json`.

## Ingestion

To build a live Neo4j from this state, ingest each grade's JSON as:

```cypher
// per concept:
MERGE (g:Grade {name: $grade})
MERGE (ch:Chapter {name: $chapter, grade: $grade})
MERGE (st:Subtopic {name: $subtopic, chapter: $chapter, grade: $grade})
MERGE (c:Concept {name: $concept_name, grade: $grade})
ON CREATE SET c.description = $description, c.glossary_validated = $gv,
              c.materi_pokok_ref = $materi_pokok_ref, c.provenance = $provenance
MERGE (g)-[:HAS_CHAPTER]->(ch)
MERGE (ch)-[:HAS_SUBTOPIC]->(st)
MERGE (st)-[:HAS_CONCEPT]->(c)

// per relation:
// (use MERGE on Concept|ConceptTarget for target as appropriate; copy
//  description + expert_review + provenance onto the rel)
```

A reference ingest script will live at `experiments/ingest_extraction_v2_reviewed.py`
(TBD when we're ready to write to a Neo4j target).

## Reproducibility

Re-running `build_extraction_v2_reviewed.py` with the same `feedback_snapshot`
produces byte-identical output. To pull fresh expert feedback and rebuild:

```bash
uv run --with redis --with certifi python experiments/redis_dump.py
python experiments/resolve_expert_feedback.py
python experiments/build_extraction_v2_reviewed.py
```
