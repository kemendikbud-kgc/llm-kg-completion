# completion-experiments/ann-classifier-v1 — derivation

## What this state is

The KG after Soros's **ANN-similarity + LLM-classifier** cross-book completion
experiment, run on top of `extraction-v2-reviewed`. Adds `LINTAS_BUKU_*` edges
between Concepts in different grades using the closed 5-type vocabulary from
`docs/yhoga-ontology.ttl:151-185`.

## Source state

`extraction-v2-reviewed` (live Yhoga Aura). The pre-completion baseline carries
3 Grade / 17 Chapter / 81 Subtopic / 342 Concept / 418 ConceptTarget and 1,064
total relationships, with **0 `LINTAS_BUKU_*` edges**.

## Methodology

Two-step pipeline implemented in `src/completion.py`:

1. **Embed + ANN similarity** (`find_similar_pairs_ann`):
   - For each `Concept`, build embed text = `name + description + materi_pokok_ref + grade`
     (`YhogaAdapter.build_embed_text`).
   - Vector index on `Concept.embedding` (`concept_embedding_idx`, cosine).
   - KNN query top-k per Concept, threshold-filtered.
   - Filter pairs to **cross-grade only** (`source.grade != target.grade`) — the
     TTL ontology defines LINTAS_BUKU_* strictly across different grades.

2. **LLM classification** (`classify_similar_pairs` with Yhoga adapter):
   - Pass each pair to LLM with prompt `_LINTAS_BUKU_BATCH_CLASSIFICATION_PROMPT`
     (or `_LINTAS_BUKU_CLASSIFICATION_PROMPT` for `batch_size=1`).
   - Prompt asks LLM to classify as one of:
     `LINTAS_BUKU_SAMA_DENGAN`, `LINTAS_BUKU_APLIKASI_DARI`,
     `LINTAS_BUKU_PRASYARAT_UNTUK`, `LINTAS_BUKU_MEMPERDALAM`,
     `LINTAS_BUKU_BERKAITAN_DENGAN`, or `none`.
   - Pydantic `LintasBukuClassification` enforces the closed vocabulary at
     parse time — no open-vocab leaks possible.
   - Output is staged to `lintas_buku_edges.json` (this folder) in the
     friend-llm dump format.

3. **Replay**: `python experiments/scripts/replay_completion.py lintas_buku_edges.json`
   MERGEs each edge into Yhoga keyed by `(Concept.name, Concept.grade)`.

## Known methodology bias

ANN+classifier is recall-limited to **surface-similar descriptions**. Strong on:
- `LINTAS_BUKU_SAMA_DENGAN` (same concept across books — descriptions overlap)
- `LINTAS_BUKU_BERKAITAN_DENGAN` (generic relatedness)

Likely under-recall on:
- `LINTAS_BUKU_APLIKASI_DARI` ("Difusi" Biology ← "Gerak Brown" Physics — concepts
  share underlying mechanism but description text does not look similar)
- `LINTAS_BUKU_MEMPERDALAM` ("Termodinamika" → "Reaksi Endoterm" — different depth
  of treatment, different phrasing)

This is a clean contrast against `friend-llm` (pure LLM emission, no ANN gate).

## Iteration log

The `ann-classifier-v1` slug captures the methodology. Each parameter sweep is
staged to its own filename (`lintas_buku_edges.t<threshold>_k<top_k>.json`);
`lintas_buku_edges.json` always points at the *canonical chosen* iteration that
will be replayed to Yhoga. Sweeps live next to it for audit.

### Iteration 1 — 2026-05-14 — `lintas_buku_edges.t085_k5.json`

Status: **staged, not replayed.** Yhoga still at pre-completion baseline.

**Params**:

```json
{
  "embed_model": "gemini/gemini-embedding-001",
  "chat_model": "gemini/gemini-2.5-flash",
  "threshold": 0.85,
  "top_k": 5,
  "scope": "cross",
  "selected_doc": "Biologi Kelas XII",
  "batch_size": 10
}
```

**Pipeline filters applied** (both ON for Yhoga in this run):

| Filter | Value | Where |
|---|---|---|
| `cross_grade_only` | True (scope=cross) | `find_similar_pairs_ann` |
| `skip_existing_typed_edges` | True | `find_similar_pairs_ann` (rule iii) |
| Pydantic vocab enforcement | 5 LINTAS_BUKU + `"none"` | `LintasBukuClassification(Item|Batch)` |

**Results**:

| Metric | Value |
|---|---:|
| Concepts indexed (with embedding) | 342 / 342 |
| SIMILAR_TO candidates after cross-grade + skip-existing filters | 15 |
| Pairs classified | 15 |
| `LINTAS_BUKU_SAMA_DENGAN` | 1 (7.7%) |
| `LINTAS_BUKU_APLIKASI_DARI` | 4 (30.8%) |
| `LINTAS_BUKU_PRASYARAT_UNTUK` | 3 (23.1%) |
| `LINTAS_BUKU_MEMPERDALAM` | 5 (38.5%) |
| `LINTAS_BUKU_BERKAITAN_DENGAN` | 0 (0%) |
| `none` (classifier rejected) | 2 |
| **Total LINTAS_BUKU_\* edges staged** | **13** |
| Confidence range | 0.85 – 1.00 |
| Open-vocab leaks | 0 (Pydantic-enforced) |

**Domain coverage**: Almost entirely Biologi ↔ Kimia molecular biology / biochemistry
(DNA cluster: 5 edges; nukleotida ↔ gen / kode genetik / DNA: 3 edges; fotosintesis
↔ pati; fosforilasi oksidatif ↔ oksidasi-reduksi organik; protein ↔ translasi;
senyawa organik / asam amino → teori evolusi kimia). **Zero Fisika links.**

**Status decision**: too sparse for thesis-scale curriculum claims. Next iteration
will drop threshold + raise top_k to widen recall before classifier rejection.

### Iteration 2 — 2026-05-14 — `lintas_buku_edges.t075_k15.json`

Status: **staged (77 edges), not yet replayed to Yhoga.**

**Params**:

```json
{
  "embed_model": "gemini/gemini-embedding-001",
  "chat_model": "gemini/gemini-2.5-flash",
  "threshold": 0.75,
  "top_k": 15,
  "scope": "cross",
  "batch_size": 10
}
```

Rationale for skipping the planned 0.80/10 ablation: cache-keying means later
iterations re-use earlier classifications for free, so the precision-recall
curve can be filled in retroactively if needed for the thesis. Operationally
we go straight to the looser end and back-fill the middle only if the result
warrants a published curve.

**SIMILAR_TO state (pre-classify)**:

| Metric | Value |
|---|---:|
| Cross-grade pairs saved | **101** (vs 15 in iteration 1, ~7× growth) |
| Within-grade leakage | 0 (both filters fired correctly) |
| Score range | 0.83 – 0.94 |
| Avg / median / p90 | 0.86 / 0.85 / 0.88 |

**Pair distribution by undirected subject pair**:

| Subjects | n | % |
|---|---:|---:|
| Kimia ↔ Biologi | 72 | 71% |
| Kimia ↔ Fisika | 24 | 24% |
| Biologi ↔ Fisika | 5 | 5% |

Iteration 1 had **zero Fisika links**. Iteration 2 has **29 cross-grade pairs
involving Fisika** (24 Kimia↔Fisika + 5 Biologi↔Fisika). This addresses the
iteration 1 domain-coverage weakness directly.

**Classify expectation**: 15/101 cache-hit from iteration 1 (zero LLM cost),
86 new pairs require classifier. At batch_size=10, ≈9 LLM batches. Expected
yield 50–80 LINTAS_BUKU_* edges (60–80% acceptance), rest classified as `"none"`.

**Results** (verified from `lintas_buku_edges.t075_k15.json`):

| Metric | Value |
|---|---:|
| Pairs classified | 101 |
| `"none"` (classifier rejected) | 24 (23.8%) |
| **Total LINTAS_BUKU_\* edges staged** | **77 (76.2% acceptance)** |
| `LINTAS_BUKU_PRASYARAT_UNTUK` | 33 (42.9%) |
| `LINTAS_BUKU_MEMPERDALAM` | 24 (31.2%) |
| `LINTAS_BUKU_APLIKASI_DARI` | 10 (13.0%) |
| `LINTAS_BUKU_BERKAITAN_DENGAN` | 9 (11.7%) |
| `LINTAS_BUKU_SAMA_DENGAN` | 1 (1.3%) |
| Unique Concepts touched | **69 / 342 = 20.2%** |
| Open-vocab leaks | 0 (Pydantic-enforced) |
| Confidence range | 0.20 – 1.00 (avg 0.85) |

**Confidence distribution** — surfaces which classifications the model was least sure about:

| Bucket | n | % |
|---|---:|---:|
| ≥ 0.95 | 19 | 24.7% |
| 0.85 – 0.95 | 37 | 48.1% |
| 0.70 – 0.85 | 14 | 18.2% |
| 0.50 – 0.70 | 2 | 2.6% |
| **< 0.50** | **5** | **6.5%** |

72.8% of edges sit at ≥0.85. The 5 below-0.50 edges should be flagged as
exploratory and spot-checked before any thesis citation that treats them as
on-par with the high-confidence majority. Filtering at confidence ≥ 0.85 would
yield 56 edges — a tighter set if precision-over-recall is the goal.

## Comparison to baselines (as of iteration 1)

Compared against the friend's notebook methodology output —
`experiments/yhoga/kg-completion/outputs/*_20260508_182633_expert_boosted.json`
(3 per-grade JSONs, identical content to `completion-experiments/friend-llm/lintas_buku_edges.json`):

| Metric | Notebook (May 8 expert-boosted) | ann-classifier-v1 (t=0.85, k=5) |
|---|---:|---:|
| Total edges | 91 | 13 |
| Concept coverage | 79 / 357 (22.1%) | ~13 / 342 (~3.8%) |
| `BERKAITAN_DENGAN` (catch-all) | 50 (54.9%) | 0 (0%) |
| `PRASYARAT_UNTUK` | 3 (3.3%) | 3 (23.1%) |
| Token-overlap fallback edges | 12 (13.2%) | 0 |
| Open-vocab leaks | 7 (BAGIAN_DARI, DIBUTUHKAN_UNTUK_PEMBENTUKAN, PENGGUNA_GAS_RUMAH_KACA) | 0 |
| Confidence per edge | ✗ | ✓ |
| Reproducibility (cached, prompt-versioned) | ✗ | ✓ |
| Cross-grade enforced by construction | ✗ | ✓ |

### Pair-level overlap with notebook: **0 / 13**

Zero common (source, target) pairs between the two methodologies. They sample
disjoint regions of the cross-book concept space because they start from
different signals:

- **Notebook**: textbook metadata (glossary terms, ToC labels, materi pokok lines)
  + open LLM emission + token-overlap fallback. Surfaces pairs whose surface forms
  or chapter headers overlap, or that the LLM judges relatable from per-chapter
  context.
- **ann-classifier-v1**: full Concept descriptions embedded into 3072-dim
  cosine-similarity space, then closed-vocab LLM classification. Surfaces pairs
  whose description-text is semantically tight.

These regions barely intersect.

### Methodological strengths confirmed (per `experiments/yhoga/kg-completion/critique.md`)

| Critique finding | ann-classifier-v1 result |
|---|---|
| §3 "typed taxonomy is present but unused" (notebook: 71% BERKAITAN_DENGAN) | 0% BERKAITAN_DENGAN; every edge committed to a structural type |
| §3 PRASYARAT_UNTUK appears once in notebook | 3 PRASYARAT_UNTUK edges (23% of output) |
| §4 "fallback is actively harmful" (notebook: 13–14% token-overlap junk) | No fallback; Pydantic-validated edges only |
| §5 hub effect on "energi" / "Metabolisme" | Not reproduced — cosine symmetric, no hub centrality artifact |
| §7 no confidence / non-determinism | Every edge has confidence ∈ [0.85, 1.00]; cache-keyed by `(pair, schema, neighborhood fp, prompt v4, model)` |
| §1 structural header leak | Impossible: matches only `:Concept`, not `:Subtopic`/`:Chapter` |

### Methodological weaknesses observed

| Limitation | Evidence |
|---|---|
| Recall ceiling from ANN gate | 13 edges vs notebook's 91. Concept coverage 3.8% vs 22.1%. |
| Domain bias toward surface-similar descriptions | All 13 edges are Biologi ↔ Kimia molecular biology. Zero Fisika links recovered, even though the notebook catches several (LED↔semikonduktor, electroplating↔arus listrik, transformator↔energi). |
| Grade tag in embed text systematically suppresses cross-grade similarity | `YhogaAdapter.build_embed_text` appends `"Mata Pelajaran: <grade>"`, pulling same-name pairs apart in embedding space. Confirmed: cross-grade scores cluster in 0.85–0.92, all within-grade in 0.90–0.98. |

## Artifacts in this folder

- `lintas_buku_edges.json` — canonical staged output, points at the chosen iteration
  for replay. Currently mirrors `lintas_buku_edges.t085_k5.json`.
- `lintas_buku_edges.t085_k5.json` — frozen iteration-1 snapshot, preserved for audit.
- `snapshot.backup.ref` — pointer (YAML) to the binary Aura `.backup` captured
  immediately after this experiment's replay (TBD until replay).
- `derivation.md` — this file.

## Reset path

To revert Yhoga to the pre-completion baseline, run:

```cypher
MATCH ()-[r]->() WHERE r.method = 'ann-classifier-v1'
DELETE r
RETURN count(r) AS deleted;
```

This is selective — preserves any other completion experiment's edges in the
same Yhoga instance. A full LINTAS_BUKU_* wipe (across all experiments) is:

```cypher
MATCH ()-[r]->() WHERE type(r) STARTS WITH 'LINTAS_BUKU' DELETE r RETURN count(r);
```

Always restore from `snapshot.backup.ref` or `extraction-v2-reviewed/snapshot.backup.ref`
if in doubt — the `.method` filter assumes the property is consistently set.

## Reproducibility

```bash
# 1. Build embeddings + similar pairs (UI: Step 5 → Find Similar Concepts)
streamlit run app.py
# (sidebar: schema=yhoga, embedding model=gemini/gemini-embedding-001,
#  chat model=gemini/gemini-2.5-flash)
# (Step 5: scope=Cross-{Grade}, threshold + top_k per iteration)

# 2. Classify and stage to JSON (UI: Step 5 → Classify & Stage to JSON)
#    Change the JSON staging path in the UI text input to the iteration's
#    filename (e.g. lintas_buku_edges.t080_k15.json) BEFORE clicking, so
#    each sweep is preserved alongside earlier ones.

# 3. Pick canonical iteration: copy chosen sweep file to lintas_buku_edges.json
#    cp lintas_buku_edges.tNNN_kMM.json lintas_buku_edges.json

# 4. Replay into Yhoga
python experiments/scripts/replay_completion.py experiments/knowledge_graph_states/completion-experiments/ann-classifier-v1/lintas_buku_edges.json

# 5. Snapshot Yhoga (manual: Aura → Take backup → record in snapshot.backup.ref)
```

## Planned subsequent iterations

- **Iteration 2 (complete, staged)**: t=0.75 / k=15 → 77 edges. See iteration log above.
- **Iteration 2.5 (optional intermediate)**: t=0.80 / k=10. Only needed if the
  thesis wants a precision-recall curve. Free in LLM cost because iteration 1
  and iteration 2 classifications are cached.
- **Iteration 3 (potential, if domain coverage still skewed)**: drop the
  `"Mata Pelajaran: <grade>"` suffix from `YhogaAdapter.build_embed_text`,
  re-embed all 342 Concepts with the grade-free embed text, then re-run
  iteration 2's params. This addresses the embedding-space grade-clustering
  bias (cross-grade scores systematically lower than within-grade). Stage to
  `lintas_buku_edges.t075_k15.no_grade_tag.json`.

The canonical `lintas_buku_edges.json` (the one replayed) is chosen *after*
comparing iteration outputs — by spot-check precision, type distribution
balance, and total coverage. The chosen iteration's file is copied to
`lintas_buku_edges.json` and that's what gets MERGEd into Yhoga.
