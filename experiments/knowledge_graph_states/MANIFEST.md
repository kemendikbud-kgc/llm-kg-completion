# KG State Manifest

Authoritative catalog of versioned KG states. Each row is a distinct,
citable state with a derivation chain back to the previous state.

| Version | Date | Source state | Derivation | Binary snapshot | Hash (sha256) | Notes |
|---|---|---|---|---|---|---|
| `v1-extraction` | 2026-05-08 (received) | — | Yhoga's per-Bab extraction pipeline (`TA_KG_INTERKONEKSI`). Output: 3 per-grade JSON files. | n/a (text only, in git) | n/a | Canonical **pre-completion** source of truth. 3 grades / 17 chapters / per-concept relations are within-book only. |
| `v2-friend-completion-llm` | 2026-05-12 (observed) | `v1-extraction` | Friend's LLM cross-book emission run. 91 `LINTAS_BUKU_*` edges added on top of v1. See `v2-friend-completion-llm/derivation.md`. | Drive (see `v2-friend-completion-llm/snapshot.backup.ref`) | TBD — fill in after Drive download | Live Yhoga Aura state as of capture. Per Concept count 406 / ConceptTarget 173. |
| `v3-pre-completion-reset` | TBD | `v2-friend-completion-llm` | `MATCH ()-[r]->() WHERE type(r) STARTS WITH 'LINTAS_BUKU' DELETE r` — strips the 91 cross-book edges. Logically equivalent to `v1-extraction` ingested into Neo4j. | TBD | TBD | Clean baseline for the A/B completion experiment. |
| `v4-your-completion-<method>` | TBD | `v3-pre-completion-reset` | Your new completion method (ANN + classifier). Adds N `LINTAS_BUKU_*` edges. | TBD | TBD | Target state for thesis evaluation vs `v2-friend-completion-llm`. |

## Conventions

- **`v<N>-<slug>`**: monotonically increasing N, descriptive slug.
- **One row per state.** No row deletions; only appends or `notes` updates.
- **Source state is exactly one prior version** (linear history). If you
  branch (e.g. retry a method with different params), make a new
  versioned folder, don't overwrite.
- **Binary snapshots are referenced, not stored** here. The
  `snapshot.backup.ref` file under each version is the source of truth
  for where the `.backup` lives.
- **`TBD` is allowed** until a state is materialized; once produced,
  fill in date + hash + URL.

## Citing in the thesis

Preferred form:

> "We evaluated method X on state `v3-pre-completion-reset` (manifest:
> `experiments/knowledge_graph_states/MANIFEST.md`, git commit
> `<sha>`)."

That sentence is unambiguous given this file + the git history.
