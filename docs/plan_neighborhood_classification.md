# Plan: Neighborhood-Augmented Relation Classification

**Goal.** Upgrade `classify_similar_pairs()` so the LLM sees each concept's existing graph neighborhood when deciding relation type, instead of classifying in isolation.

**Thesis framing.** Turns the pipeline from "retrieval + typing in a vacuum" into "retrieval + contextualized reasoning" — closer to what the LLM-KGC literature calls *context-augmented link prediction*. Provides a clean with/without ablation for the thesis results chapter.

---

## Why this change

Current `classify_similar_pair()` in `src/completion.py` sees only:

- `name`, `description` of A and B
- `formula`, `variables`, `kondisi` of A and B

It does **not** see:

- A's existing out-edges (what A already `isPrerequisiteOf` / `supports` / `analogousTo`)
- B's existing out-edges
- Whether A and B share any neighbors
- Whether A and B live in the same Bab

These are the strongest signals for typing a new relation. A concept that's already prerequisite-of three other concepts in Bab 2 is very likely prerequisite-of yet another Bab 2 concept. The current classifier has to rediscover this from scratch every call.

---

## Success criteria

1. **Behavioral:** For any pair (A, B) fed to classification, the prompt includes up to *k* existing typed out-edges for A and for B (names + relation types), plus any shared-neighbor signal.
2. **Measurable:** On a held-out sample of 50 hand-labeled pairs, neighborhood-augmented classifier agrees with ground truth at a higher rate than the baseline (target: +10 pp precision on at least two of `isPrerequisiteOf` / `supports` / `analogousTo`).
3. **Thesis-usable:** Produce a comparison table `(method, rel_type, precision, recall, F1)` for both variants, suitable for a results section.
4. **Safe rollback:** The neighborhood-augmented path is toggleable via a config flag (no removal of the original baseline).

---

## Design

### Data to collect per concept

For each concept node `N` involved in classification, fetch from Neo4j:

```cypher
MATCH (n:Konsep|SubKonsep {name: $name})
OPTIONAL MATCH (n)-[r:isPrerequisiteOf|supports|analogousTo]->(target)
WITH n, r, target
RETURN n.name AS name,
       collect({rel_type: type(r), target: target.name,
                confidence: r.confidence})[0..5] AS out_edges,
       [(n)<-[:hasKonsep|hasSubKonsep]-(b:Bab) | b.name][0] AS bab
```

Result per concept:

```json
{
  "name": "Hukum Newton II",
  "bab": "Dinamika Gerak",
  "out_edges": [
    {"rel_type": "supports", "target": "Gaya Gesek", "confidence": 0.82},
    {"rel_type": "isPrerequisiteOf", "target": "Momentum", "confidence": 0.74}
  ]
}
```

Cap at 5 out-edges per concept to bound prompt size. Prefer highest-confidence ones.

### Prompt extension

Add a new section to `_CLASSIFICATION_PROMPT`:

```
========================
KONTEKS GRAF (HUBUNGAN YANG SUDAH ADA)
========================
Konsep A ("{name_a}") berada di Bab: {bab_a}
Hubungan A yang sudah ada di graf:
  - isPrerequisiteOf → "Momentum" (conf: 0.74)
  - supports → "Gaya Gesek" (conf: 0.82)

Konsep B ("{name_b}") berada di Bab: {bab_b}
Hubungan B yang sudah ada di graf:
  - (tidak ada)

Shared neighbors: {shared_neighbors or "tidak ada"}

Gunakan konteks graf ini sebagai bukti tambahan. Jika A sudah punya banyak
hubungan `isPrerequisiteOf` dengan konsep di Bab yang sama dengan B,
klasifikasi `isPrerequisiteOf` lebih mungkin benar.
```

### Schema / code changes

Three file touches, all additive:

| File | Change |
|---|---|
| `src/graph.py` | Add `get_concept_context(driver, names, limit=5) -> dict` helper returning neighborhood data for a batch of node names. |
| `src/completion.py` | Extend `_CLASSIFICATION_PROMPT` with the new context section. Extend `classify_similar_pair()` to accept neighborhood kwargs. Modify `classify_similar_pairs()` to fetch contexts in one round trip before the loop. Bump `CLASSIFICATION_PROMPT_VERSION = "v3"` (invalidates prior cache). |
| `src/config.py` | Add `CLASSIFY_WITH_NEIGHBORHOOD = True` flag. Add `NEIGHBORHOOD_MAX_EDGES = 5` constant. |

No change to `pages/5_Completion.py` — the UI button calls `classify_similar_pairs()` which internally picks up the new behavior.

---

## Implementation steps

### Step 1 — Neighborhood fetcher in `src/graph.py`

Add after `get_nodes_with_current_embedding()`:

```python
def get_concept_context(
    driver,
    names: list[str],
    max_edges: int = 5,
) -> dict[str, dict]:
    """Fetch graph context for a batch of Konsep/SubKonsep nodes.

    Returns {name: {"bab": str|None, "out_edges": [{rel_type, target, confidence}]}}.
    Out-edges sorted by confidence desc, capped at max_edges.
    """
    if not names:
        return {}
    with driver.session() as session:
        result = session.run(
            """
            MATCH (n) WHERE (n:Konsep OR n:SubKonsep) AND n.name IN $names
            OPTIONAL MATCH (n)-[r:isPrerequisiteOf|supports|analogousTo]->(t)
            OPTIONAL MATCH (n)<-[:hasKonsep|hasSubKonsep]-(b:Bab)
            WITH n, b,
                 collect({rel_type: type(r), target: t.name, confidence: r.confidence}) AS edges
            RETURN n.name AS name,
                   head(collect(DISTINCT b.name)) AS bab,
                   [e IN edges WHERE e.target IS NOT NULL] AS out_edges
            """,
            names=names,
        )
        contexts = {}
        for r in result:
            edges = sorted(
                r["out_edges"],
                key=lambda e: (e.get("confidence") or 0.0),
                reverse=True,
            )[:max_edges]
            contexts[r["name"]] = {
                "bab": r["bab"],
                "out_edges": edges,
            }
        # Nodes not found: empty context
        for n in names:
            contexts.setdefault(n, {"bab": None, "out_edges": []})
        return contexts
```

### Step 2 — Prompt update in `src/completion.py`

Bump version:

```python
CLASSIFICATION_PROMPT_VERSION = "v3"  # was v2
```

Replace `_CLASSIFICATION_PROMPT` with an extended version containing the new `KONTEKS GRAF` block. Keep the existing rumus/variabel/kondisi block.

### Step 3 — Function signatures

```python
def classify_similar_pair(
    name_a, desc_a,
    name_b, desc_b,
    llm_model=None,
    formula_a=None, variables_a=None, kondisi_a=None,
    formula_b=None, variables_b=None, kondisi_b=None,
    # new ↓
    bab_a: str | None = None,
    out_edges_a: list[dict] | None = None,
    bab_b: str | None = None,
    out_edges_b: list[dict] | None = None,
    shared_neighbors: list[str] | None = None,
) -> tuple[str, float]:
```

Helper to format out-edges into prompt text:

```python
def _format_out_edges(edges: list[dict] | None) -> str:
    if not edges:
        return "(tidak ada)"
    return "\n".join(
        f"  - {e['rel_type']} → \"{e['target']}\" (conf: {e.get('confidence', 0.0):.2f})"
        for e in edges
    )
```

### Step 4 — Wire context into `classify_similar_pairs()`

Single-batch Neo4j fetch for all names involved, before the classification loop:

```python
names = list({p["source"] for p in pairs} | {p["target"] for p in pairs})
# existing: node_map fetch for formula/variables/kondisi
contexts = get_concept_context(driver, names, max_edges=NEIGHBORHOOD_MAX_EDGES)

for pair in pairs:
    source, target = pair["source"], pair["target"]
    ctx_a = contexts.get(source, {})
    ctx_b = contexts.get(target, {})
    shared = _compute_shared_neighbors(ctx_a, ctx_b)  # small helper
    # ... inside the non-cache branch, pass bab_a, out_edges_a, ... to classify_similar_pair
```

### Step 5 — Config flag

In `src/config.py`:

```python
CLASSIFY_WITH_NEIGHBORHOOD = True
NEIGHBORHOOD_MAX_EDGES = 5
```

In `classify_similar_pairs()`, wrap the context fetch:

```python
from src.config import CLASSIFY_WITH_NEIGHBORHOOD, NEIGHBORHOOD_MAX_EDGES

contexts = (
    get_concept_context(driver, names, max_edges=NEIGHBORHOOD_MAX_EDGES)
    if CLASSIFY_WITH_NEIGHBORHOOD else {}
)
```

When flag is `False`, contexts is empty and the prompt falls back to the baseline behavior. Same prompt template handles both cases via conditional formatting (show the KONTEKS GRAF block only when `out_edges` is non-empty).

### Step 6 — Cache invalidation

`CLASSIFICATION_PROMPT_VERSION = "v3"` is already the cache key. Bumping it naturally invalidates all v2 classifications without manual cache deletion.

---

## Testing and validation

### Unit test (manual, one-off)

Construct a known pair with mock neighborhood and check prompt formatting:

```python
ctx_a = {"bab": "Dinamika", "out_edges": [
    {"rel_type": "isPrerequisiteOf", "target": "Momentum", "confidence": 0.8}
]}
# ... call classify_similar_pair with explicit kwargs
# Assert: rel_type is one of the 4 literals, confidence in [0, 1]
```

### Ablation pilot (thesis-usable)

1. **Draw a gold set.** Hand-label 50 pairs from the current graph (post-0.85 threshold run): 30 positives (real relations) + 20 negatives (similar but not pedagogically linked). For each positive, label the correct relation type.
2. **Baseline run.** Set `CLASSIFY_WITH_NEIGHBORHOOD = False`, classify the 50 pairs. Record `(predicted_type, confidence, is_correct)`.
3. **Augmented run.** Flip flag to `True`, classify the same 50 pairs (cache won't collide — v3 vs v2). Record same metrics.
4. **Compare.** Precision, recall, F1 per relation type. Confusion matrix for both.
5. **Statistical test.** McNemar's test on paired predictions — cheap, reports whether the difference is significant.

### Expected outcomes (hypothesis for thesis)

- **Precision on `isPrerequisiteOf`:** augmented > baseline (biggest win — the baseline rarely predicts this class at all, neighborhood context should help it identify prerequisite chains).
- **Recall on `analogousTo`:** roughly unchanged (analogy is about cross-domain structural similarity; neighborhood of each concept is domain-local).
- **"none" rate:** augmented slightly lower (context clarifies borderline cases).

---

## Risks and open questions

1. **Prompt budget.** Adding 5 out-edges × 2 concepts × ~80 chars each = ~800 extra chars per call. Fine for gemini-flash-lite (1M context). No action needed.

2. **Circular reasoning.** If out-edges were themselves produced by a prior run of this classifier, the LLM sees its own past (noisy) decisions as "evidence." Mitigation: on first run the graph has zero typed edges, so this is a non-issue. On re-runs, confidence-threshold the context (only show edges with `confidence >= 0.7` in the prompt) to avoid compounding low-confidence errors.

3. **Cache miss cost.** v2 → v3 invalidates all prior classifications. For ~500 pairs that's one extra classification run (~1–2 min on gemini-flash-lite). Acceptable.

4. **Bab attribution for SubKonsep.** The Cypher pattern `n<-[:hasKonsep|hasSubKonsep]-(b:Bab)` needs verification — SubKonsep attaches via `hasSubKonsep` from Konsep, not from Bab directly. Check actual schema; may need a two-hop match.

5. **Shared-neighbors definition.** Is it "both A and B have an edge to X" or "A-[any]-X and B-[any]-X"? Start simple (same target node, ignoring relation direction/type), refine if signal is noisy.

6. **Non-determinism contamination.** If gemini-flash-lite runs at default temperature, re-running the same ablation gives different numbers each time. Set `temperature=0` or fix a seed in the LlamaIndex `LLMTextCompletionProgram` config before the ablation — otherwise the thesis comparison is unreproducible.

---

## Out of scope

- **Graph structure-based candidate generation** (finding new pairs via 2-hop paths). That's Option B from the earlier discussion; treat as future work.
- **Rule-induction baseline** (AMIE/AnyBURL). Option C, high effort.
- **Direct generative KGC** (hit@K evaluation). Option D, full retrain setup.
- **Changing the relation taxonomy.** Keep `isPrerequisiteOf` / `supports` / `analogousTo` / `none` as-is.
- **Re-running embedding extraction.** Embeddings unchanged.

---

## Estimated effort

| Task | Hours |
|---|---:|
| Add `get_concept_context()` helper + unit-check via MCP | 0.5 |
| Extend prompt + `classify_similar_pair()` signature | 1.0 |
| Wire into `classify_similar_pairs()` batch flow | 1.0 |
| Config flag + prompt conditional | 0.5 |
| Hand-label 50-pair gold set | 2.0 |
| Ablation run (both flags) + metric computation | 1.0 |
| Write thesis section on the ablation | 2.0 |
| **Total** | **8.0** |

~1 working day. Fits a thesis sprint.

---

## Proposed next step

1. Confirm this plan (or request changes).
2. Implement Steps 1–5 in one session.
3. Leave Step 6 (gold set + ablation) as a separate work item — it's the thesis-evidence part and doesn't need to block code landing.

Post-implementation, add an entry to `experiment_log.md` tagged `v3-neighborhood` so the results are traceable.
