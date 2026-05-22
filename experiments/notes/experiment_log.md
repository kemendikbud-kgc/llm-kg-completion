# Experiment Log

Running log of KG completion experiments.

---

## 2026-04-24 — Embedding-based similarity search, run 1

**Pipeline step:** KG Completion (Step 5, "Find Similar Konsep")

**Configuration**

| Parameter | Value |
|---|---|
| Embedding model | `gemini/gemini-embedding-001` (3072-dim) |
| Vector index | `konsep_embedding_idx` + `subkonsep_embedding_idx`, HNSW, cosine, quantization enabled |
| Similarity threshold | 0.80 |
| Neighbors per node (top-k) | 10 |
| Scope | All documents |

**Graph state at run time**

- 511 Konsep nodes, 100% with embeddings (same model across all).
- 0 SubKonsep nodes.

**Result**

- **3053 `SIMILAR_TO` relationships** found and written to the graph.
- Approx 6.0 similar pairs per Konsep on average.

**Notes**

- Fixed a vector-index dimension bug prior to this run: `get_embedding_dimensions()` in `src/graph.py` had `"gemini-embedding": 768`, but `gemini-embedding-001` outputs 3072-dim by default. Index recreated at 3072. Before the fix, "Find Similar" returned 0 pairs because Neo4j silently rejected dimensionally mismatched query vectors.
- Classification step (Step 5b) not yet run on these pairs.

**Next**

- Run Step 5b to classify these 3053 pairs into `isPrerequisiteOf` / `supports` / `analogousTo` / `none`.
- Consider sweeping threshold (e.g. 0.75, 0.85, 0.90) to study precision/recall tradeoff.
