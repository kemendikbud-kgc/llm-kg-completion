# `experiments/` — map

What lives where, and what each subfolder is for.

## Pipeline tooling — `scripts/`

Reusable scripts that drive the pipeline. Rerun many times against different
inputs. Tracked in git. Invoke from repo root, e.g.
`python experiments/scripts/replay_completion.py <path>`.

| Script | Purpose |
|---|---|
| `build_extraction_v2_reviewed.py` | Build the `extraction-v2-reviewed` KG snapshot from extraction-v1 + expert resolutions. |
| `ingest_extraction_v2_reviewed.py` | Ingest the v2 snapshot into Yhoga Neo4j Aura. |
| `replay_completion.py` | MERGE LINTAS_BUKU_* edges from a staged JSON dump into Neo4j. The canonical replay entrypoint referenced by `derivation.md`. |
| `dump_lintas_buku.py` | Dump the current LINTAS_BUKU_* state from Yhoga to JSON. |
| `resolve_expert_feedback.py` | Apply expert review labels back to the extraction JSON. |
| `expert_review_analysis.py` | Aggregate Phase 1 expert validation responses → precision / recall / F1 / κ. |
| `thesis_results_sheet.py` | Write thesis results tables to the Google Sheets workbook. |
| `redis_check.py`, `redis_dump.py` | KG Review App health and dump helpers. |

## One-shot audits — `audits/`

Inspections that ran once during a specific investigation. Kept for
reproducibility but not part of the regular pipeline.

| Script | What it investigated |
|---|---|
| `check_yhoga_embeddings.py` | Whether the Yhoga upstream has `Concept.embedding` set (it doesn't). |
| `compare_annv1_vs_new.py` | Head-to-head: `yhoga-ann-v1/` outputs vs `yhoga-boosted-peer/` `_expert_boosted` cross-book links. |
| `diff_thesis_tabs.py` | Outline diff: thesis doc's `Main` vs `Formatted Main` tabs. |
| `extract_bab4_dev.py`, `extract_thesis_sections.py` | Pull specific tabs/sections out of the thesis doc cache. |
| `extract_yhoga_params.py` | Regex-scrape LLM/embedding/chunking params from Yhoga's notebooks. |

## Notes & methodology — `notes/`

Markdown notes that aren't full docs but are too important to be cache.

| Note | Topic |
|---|---|
| `EXPERT_FEEDBACK_CONTEXT.md` | Context for Phase 1 expert validation. |
| `parameter_sistem_v2.md` | Revised LLM/embedding parameter table for Bab 3 (derived from Yhoga notebooks). |
| `experiment_log.md` | Running log of completion-experiment iterations. |

## Canonical KG snapshots — `knowledge_graph_states/`

Versioned KG states. Each subfolder is a named snapshot with a `derivation.md`,
per-book JSON dumps, and a `snapshot.backup.ref` pointing at the Neo4j Aura
binary backup. See `MANIFEST.md` for the index.

## Per-experiment artifacts (self-contained)

| Folder | What it is |
|---|---|
| `yhoga-ann-v1/` | Canonical ann-classifier-v1 completion run outputs (`lintas_buku_edges*.json`, `derivation.md`, pitch). Mirrors `knowledge_graph_states/completion-experiments/ann-classifier-v1/`. |
| `yhoga-boosted-peer/` | Downloaded peer (Yhoga) `_expert_boosted.json` outputs + comparison scripts (`compare.py`, `judge_kg.py`, `quantify_boost.py`). |
| `yhoga/` | Mirror of Yhoga's notebook repo (`TA_KG/`, `kg-completion/`). Includes `kg-completion/ANN_CLASSIFIER_V1.ipynb` — the configurable notebook port of `src/completion.py` for him. |
| `tegar/` | Mirror of Tegar's experiment notebooks + dashboards. |

## Scratch — `.cache/` (gitignored)

Regeneratable dumps from one-shot exploration. Includes the 7 MB Google Doc
JSON, flat-text dumps of thesis tabs, and superseded thesis-draft snapshots
preserved here in case they're useful for diffs but not authoritative.
