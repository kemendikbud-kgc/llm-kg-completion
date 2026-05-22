# KG State Manifest

Authoritative catalog of versioned KG states. States are split into two axes:

- **Ingestion axis** (`extraction-v1`, `extraction-v2-reviewed`, …): what the
  pre-completion KG contains. Each version is a refinement over the previous.
- **Completion-experiments axis** (`completion-experiments/<slug>/`): cross-book
  edges produced by a specific completion method on top of one ingestion state.
  Multiple experiments can branch off the same ingestion baseline.

## Ingestion states (canonical line)

| Version | Date | Source state | Derivation | Binary snapshot | Hash (sha256) | Notes |
|---|---|---|---|---|---|---|
| `extraction-v1` | 2026-05-08 (received) | — | Yhoga's per-Bab extraction pipeline (`TA_KG_INTERKONEKSI`). Output: 3 per-grade JSON files. | Drive `extraction-v1/` (3 JSONs + derivation.md) | n/a | Raw extraction output. 3 grades / 17 chapters / 557 within-book triples. |
| `extraction-v2-reviewed` | 2026-05-13 | `extraction-v1` + expert feedback (Redis snapshot `redis_snapshot_2026-05-13`) | Built offline by `experiments/build_extraction_v2_reviewed.py`: 552 v1 triples retained (with per-relation `expert_review` annotations), 5 dropped per `consensus='wrong'`, 29 reviewer-proposed triples appended under synthetic "Expert Proposed Triples" subtopics. Single-reviewer drops honored and audited in `dropped_triples.json`. | TBD — produced after first Neo4j ingest | TBD | **Team's shared canonical pre-completion baseline.** Total relations: 581 (552 retained + 29 proposed). Downstream completion experiments must run against this state. |

## Completion experiments (branches)

| Slug | Date | Source state | Derivation | Binary snapshot | Hash (sha256) | Notes |
|---|---|---|---|---|---|---|
| `completion-experiments/friend-llm` | 2026-05-12 (observed) | `extraction-v1` (live Yhoga Aura at the time) | Friend's LLM cross-book emission run. 91 `LINTAS_BUKU_*` edges added on top of v1. See `completion-experiments/friend-llm/derivation.md`. | Drive (see `completion-experiments/friend-llm/snapshot.backup.ref`) | TBD — fill in after `.backup` is identified | Live Yhoga Aura state as of capture. Per Concept count 406 / ConceptTarget 173 / total relationships 1,654. |
| `completion-experiments/ann-classifier-v1` | TBD (run pending) | `extraction-v2-reviewed` | Soros's ANN-similarity + LLM-classifier run on the canonical baseline. Cosine top-k per Concept above threshold, then LLM classifies into the 5-type closed `LINTAS_BUKU_*` vocab from `docs/yhoga-ontology.ttl`. Cross-grade only. JSON-staged then MERGEd into Yhoga via `experiments/scripts/replay_completion.py`. See `completion-experiments/ann-classifier-v1/derivation.md`. | TBD (Aura `.backup` taken post-replay) | TBD | First completion experiment on the `extraction-v2-reviewed` baseline. |

## Conventions

- **Ingestion folders**: `extraction-v<N>[-<descriptor>]`. Linear N, append-only.
- **Completion folders**: `completion-experiments/<method-slug>/`. Multiple
  experiments per ingestion baseline are fine; the source state is named in
  each folder's `derivation.md`.
- **One row per state.** No row deletions; only appends or `notes` updates.
- **Binary snapshots are referenced, not stored** in git. Each folder has a
  `snapshot.backup.ref` with the Drive URL/file ID + sha256 + size.
- **`TBD` is allowed** until a state is materialized; once produced, fill in
  date + hash + URL.

## Citing in the thesis

Preferred form:

> "We evaluated method X on state `extraction-v2-reviewed` (manifest:
> `experiments/knowledge_graph_states/MANIFEST.md`, git commit `<sha>`)."

That sentence is unambiguous given this file + the git history.
