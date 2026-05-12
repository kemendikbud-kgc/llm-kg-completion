# v1-extraction — derivation

## What this state is

The canonical **pre-completion** KG, produced by Yhoga's per-Bab
extraction pipeline before any cross-book completion step ran.

The three JSON files in this folder are per-grade dumps:

- `Biologi Kelas XII.json`
- `Fisika Kelas XII.json`
- `Kimia Kelas XII.json`

## Structure of each file

```
grade
└── chapters[]
    ├── chapter            (name)
    ├── chapter_summary    (1–3 sentence academic summary)
    ├── previous, next     (sequential chapter order within the book)
    ├── subchapters[]      (high-level partitions)
    └── subtopics[]
        └── concepts[]
            ├── name
            ├── description
            ├── glossary_validated   (bool)
            ├── materi_pokok_ref     (Kurikulum Merdeka anchor)
            └── relations[]
                ├── type             (relation name, e.g. MEMILIKI_SIFAT, MENGATUR, …)
                ├── target           (target concept name)
                └── description      (1-sentence reason)
```

All `relations` here are **within-book** (target is a concept in the
same book / Bab). No `LINTAS_BUKU_*` relations exist in this state.

## How it was produced

By Yhoga's pipeline (`TA_KG_INTERKONEKSI` — see
`experiments/yhoga/TA_KG/` notebooks). Per-Bab LLM extraction emitted
the `chapter_summary`, the per-concept records, and the within-book
relations. Source PDFs: `Biologi_BS_KLS_XII_Rev.pdf`,
`Fisika_BS_KLS_XII.pdf`, `Kimia_BS_KLS_XII.pdf`
(Kurikulum Merdeka, Kelas XII).

## Caveats

The relation `type` vocabulary in `relations[]` is **open**, not the
8 closed within-book types declared in `docs/yhoga-ontology.ttl`.
Types like `MEMILIKI_SIFAT`, `MENGATUR`, `TERDIRI_DARI`, and many others
appear. This is an extraction-time artefact, not a completion-step
output, and is consistent across all three grades.

## Ingest

To rebuild a live KG from this state, ingest each JSON into Neo4j as:

```
(Grade {name})-[:HAS_CHAPTER]->(Chapter {name, summary, grade})
              -[:HAS_SUBTOPIC]->(Subtopic {name, chapter, grade})
              -[:HAS_CONCEPT]->(Concept {name, description, glossary_validated, materi_pokok_ref, grade})
```

Chapter sequencing: `(Chapter)-[:NEXT_CHAPTER]->(Chapter)` from
the `next` field. Within-book concept relations: emit edges of
`type` from each concept to the target (using `ConceptTarget` if
the target hasn't been extracted as a full Concept yet).
