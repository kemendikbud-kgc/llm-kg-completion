# completion-experiments/friend-llm — derivation

## What this state is

The KG after the friend's LLM-driven cross-book completion experiment
ran on top of `extraction-v1`. Adds **91 `LINTAS_BUKU_*` edges** between
Concepts in different grades. No nodes added; only new edges and edge
properties.

## Source state

`extraction-v1` (ingested into Neo4j as the Yhoga Aura Free instance).

## Derivation summary

- **Method**: pure LLM emission (no ANN/similarity step).
- **No vector index, no embeddings** on Concept nodes (confirmed at
  capture time: 0 of 406 Concepts have `embedding`).
- **Direction**: LLM was prompted with pairs/triples of Concepts across
  grade boundaries, returning a `relation_type` (closed-ish vocabulary,
  see below) and a 1-sentence `description`. Each edge was MERGE'd as
  `[:LINTAS_BUKU_<relation_type> {description, relation_type}]`.
- **TODO from friend**: exact LLM model, prompt version, date of run,
  whether the prompt enforced the 5-type closed vocabulary from
  `yhoga-ontology.ttl`.

## Edge breakdown at capture (2026-05-12)

| `rel_type`                                | n  | In ontology TTL? |
|---|---:|---|
| `LINTAS_BUKU_BERKAITAN_DENGAN`            | 50 | ✅ |
| `LINTAS_BUKU_APLIKASI_DARI`               | 13 | ✅ |
| `LINTAS_BUKU_MEMPERDALAM`                 | 13 | ✅ |
| `LINTAS_BUKU_SAMA_DENGAN`                 |  5 | ✅ |
| `LINTAS_BUKU_BAGIAN_DARI`                 |  4 | ❌ (`SAMA_DENGAN/APLIKASI_DARI/MEMPERDALAM/BERKAITAN_DENGAN/PRASYARAT_UNTUK` are the 5 declared) |
| `LINTAS_BUKU_PRASYARAT_UNTUK`             |  3 | ✅ |
| `LINTAS_BUKU_DIBUTUHKAN_UNTUK_PEMBENTUKAN` | 2 | ❌ open-vocab leak |
| `LINTAS_BUKU_PENGGUNA_GAS_RUMAH_KACA`     |  1 | ❌ open-vocab leak |
| **Total**                                 | **91** | |

The 7 edges in non-TTL types are **open-vocabulary leaks** — the friend's
prompt did not strictly enforce the 5-type closed vocabulary. Worth
discussing with Yhoga before evaluation.

## Live instance counts at capture

| Label / metric | Count |
|---|---:|
| Concept | 406 |
| ConceptTarget | 173 |
| Subtopic | 77 |
| Chapter | 17 |
| Grade | 3 |
| Total relationships | 1,654 |
| `LINTAS_BUKU_*` edges | 91 |

## Artifacts in this folder

- `lintas_buku_edges.json` — all 91 edges as a text-diffable JSON dump
  (source/target Concept name + grade, rel_type, properties). Replayable
  into a Neo4j via `UNWIND` + `MATCH`+`MERGE`. Captured 2026-05-13.
- `snapshot.backup.ref` — pointer (YAML) to the binary `.backup` file
  stored in Drive.

## Reset path

To revert the live Yhoga Aura to its pre-completion form, run:

```cypher
MATCH ()-[r]->() WHERE type(r) STARTS WITH 'LINTAS_BUKU'
DELETE r
RETURN count(r) AS deleted;   -- expect 91
```

This is reversible from the `.backup` snapshot or by replaying
`lintas_buku_edges.json`. For the team's canonical pre-completion
baseline, ingest `extraction-v2-reviewed/` instead (richer than the
mere reset, since it folds in the expert feedback).
