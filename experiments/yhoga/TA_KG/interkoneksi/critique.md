# Critique: Notebook's Cross-Book Interconnection Step

**Scope:** The `cross_book_links` generation inside `TA_KG_INTERKONEKSI.ipynb` (`extract_triplets` in cell 12), which ships typed cross-book edges between Biologi, Fisika, and Kimia Kelas XII concepts.

**Dataset analyzed:** `Biologi Kelas XII20260415_021115.json`, `Fisika Kelas XII20260415_021115.json`, `Kimia Kelas XII20260415_021115.json` in this directory — 63 total `cross_book_links` across 359 concepts.

**Analysis date:** 2026-04-24.

---

## Data summary

| Book | Chapters | Concepts | w/ ≥1 link | Coverage | Total links |
|---|---:|---:|---:|---:|---:|
| Biologi Kelas XII | 4 | 102 | 12 | 11.8% | 16 |
| Fisika Kelas XII | 9 | 148 | 26 | 17.6% | 28 |
| Kimia Kelas XII | 4 | 109 | 14 | 12.8% | 19 |
| **Total** | **17** | **359** | **52** | **14.5%** | **63** |

**Relation type distribution:**

```
BERKAITAN_DENGAN    71.4%    ← catch-all
MEMPERDALAM         12.7%
SAMA_DENGAN          7.9%
APLIKASI_DARI        6.3%
PRASYARAT_UNTUK      1.6%    ← one edge in the entire curriculum
```

**Source → target matrix:**

```
FROM ↓ / TO →     Biologi   Fisika   Kimia
Biologi              —         1      15
Fisika              10         —      18
Kimia               13         6       —
```

**LLM vs fallback split:**

- LLM-produced: 54 (85.7%)
- Token-overlap fallback (`infer_cross_links`): 9 (14.3%)

---

## 1. Signal choice: wrong starting material

The notebook uses glossary terms + TOC labels + "materi pokok" lines as the cross-book candidate pool. This is **cheap metadata, not semantic content.** Three structural problems follow:

- **Selection bias inherited from textbook authors.** What's in the glossary reflects editorial judgment, not pedagogical connectivity. Authors omit foundational terms they deem already known, and include narrow technical vocabulary that has no cross-subject analogue.
- **Surface forms, not meanings.** "Laju reaksi" in kimia ≠ "kecepatan proses" in biologi at the string level but they encode the same principle. Any string-matched approach is blind to this.
- **Structural headers leak into the concept pool.** Confirmed in the data: `"Subbab A. Sifat dan Konsep Asam Basa"` appears as a `target_concept` twice. The pipeline is happily linking concepts to subchapter labels because `collect_other_books_context()` ingests `chapter_names + subchapter_names` as candidates. Silent data-quality bug.

---

## 2. Prompt design conflates two tasks

`extract_triplets()` asks a single `gemini-2.5-flash-lite` call to do three things at once:

1. Extract concepts from the chapter
2. Write relations between them
3. Propose cross-book links to other textbooks

Forcing one prompt to do all three trades attention. Evidence in the output:

- **Only 14.5% of concepts have any cross-book link.** When the LLM is working hard on within-chapter extraction, cross-book linking becomes an afterthought.
- **Asymmetry:** Biologi → Fisika = 1 edge, Fisika → Biologi = 10. For `SAMA_DENGAN` (symmetric by definition), this should be roughly equal. It isn't, because the linking outcome depends on *which chapter is being extracted at the moment* — the LLM sees a different candidate list each call.

Two-stage separation (extraction first, linking second) would let the linking stage see all extracted concepts from all books simultaneously instead of a fragmentary per-chapter view.

---

## 3. Typed taxonomy is present but unused

Five relation types are defined: `SAMA_DENGAN`, `APLIKASI_DARI`, `PRASYARAT_UNTUK`, `MEMPERDALAM`, `BERKAITAN_DENGAN`. **Seven out of ten edges are the weakest possible tag.**

Specific misclassification confirmed in the sample:

- `Gaya Magnet pada Muatan Bergerak → muatan` — explanation literally says *"konsep muatan listrik adalah dasar untuk memahami gaya magnet"*. That's the definition of `PRASYARAT_UNTUK`. Tagged `BERKAITAN_DENGAN`.

The prompt asks for the type but doesn't force the LLM to justify *why not one of the stricter types*. That single prompt change would redistribute mass toward the informative tags.

---

## 4. Fallback is actively harmful

`infer_cross_links()` fires when the LLM returns no links. It uses token overlap ≥ 2 words after stopword removal. Accounts for 14.3% of all edges. **Every sampled fallback edge is defective:**

- `Komponen Bioteknologi → Senyawa Organik Tersusun atas Rantai Karbon`
  Shared tokens: **"atas", "tersusun"**. These are generic Indonesian function words, not scientific terms. The stopword list missed them.
- `Nukleotida → Subbab A. Sifat dan Konsep Asam Basa`
  Shared tokens: "asam", "basa" — but the "asam" in *asam nukleat* is nucleic acid, unrelated to *asam-basa* chemistry. A classic polysemy trap.
- `Pelapisan Logam (Electroplating) → LISTRIK ARUS SEARAH` AND `→ Arus Listrik`
  Two near-duplicate targets from the same source because `LISTRIK ARUS SEARAH` is a chapter name that leaked into the concept pool (see §1).

The fallback is optimized to *produce links* rather than *produce correct links*. It pads recall at the cost of precision in a way that's invisible to the output consumer — there's no field distinguishing fallback links from LLM links in the saved JSON.

---

## 5. Hub effect on semantic sinks

Most-linked target concepts:

```
Metabolisme             × 5
Sintesis Protein        × 5
Arus Listrik            × 5
energi                  × 4   ← generic
asam amino              × 4
bilangan oksidasi       × 3   ← stretched applicability
```

`energi` is a semantic sink. Four incoming edges including *"Transformator → energi: Transformator berperan dalam efisiensi transmisi energi listrik."* Trivially true; carries no discrimination. Nearly any physics concept could link to "energi" this way. A rank-by-specificity filter would strip these.

---

## 6. Coverage is too sparse to be pedagogically useful

- 63 total cross-book edges across 359 concepts.
- ~85% of concepts have **zero** cross-book links.
- Mean 0.17 links per concept.

For a curriculum-completion thesis, this is too sparse to support claims like "our method identifies pedagogical bridges across subjects." It identifies a handful and misses the rest. Worse, sparsity correlates with which book's chapter is being extracted — not with actual connectedness.

---

## 7. No ground truth, no precision/recall reporting

The notebook produces links and writes them to Neo4j. There is no held-out gold set, no spot-check protocol, no confidence score, no version pin on the LLM. For a thesis evaluation:

- **You can't defend what you don't measure.** Right now there's no way to report "X% of cross-book links were judged valid by domain experts."
- **LLM non-determinism is not controlled** — no temperature, seed, or `top_p` set in the `generate_content` call. Re-running produces different links.
- **No per-link confidence** — every edge is treated as equally reliable. The LLM links and the fallback links are indistinguishable in the output.

---

## 8. Poor scalability to more books

`collect_other_books_context()` hardcodes `limit_per_book = 80`, shown as `[:20]` in the prompt. For 3 books that's ~40 other-book candidates. For 10 books it's ~180, dominating the prompt and forcing dilution. The approach has a book-count ceiling baked into prompt budget — it's a pilot study method, not an extensible system.

---

## How the embedding-based approach responds

| Notebook weakness | Embedding-based pipeline's response |
|---|---|
| Glossary surface-form signal | Learned 3072-dim embedding of the concept's full description |
| Single-call conflation | Two stages: embed (retrieval) → LLM classify (typing) |
| Typed taxonomy unused | Classifier sees only semantically close pairs, so typing is less distracted |
| Token-overlap fallback junk | No string-match fallback in the pipeline |
| Source/target asymmetry | Cosine similarity is symmetric by construction |
| Hub effect on "energi" | Detectable as a centrality outlier in the similarity graph |
| Coverage sparse | Tunable via `threshold` + `top_k`; can sweep to find the operating point |
| Book-count ceiling | No per-book prompt budget — scales with vector index |
| No confidence score | Both `SIMILAR_TO.score` and typed relation `confidence` are stored |

---

## Thesis framing suggestions

Two angles that would land well:

1. **"Metadata-based vs. embedding-based cross-subject linking on the Kelas XII curriculum."** Present the notebook as Baseline A, the embedding pipeline as Method B, rate N links from each by 1–2 domain experts, report precision/recall per relation type. The numbers already look favorable — 71% catch-all in the baseline is easy to beat on typed-relation accuracy.

2. **"Pitfalls of string-signal curriculum mining."** Use the fallback-link catalogue above (especially the "atas/tersusun" and "asam-basa polysemy" cases) as a motivating example for why surface features fail in multilingual, domain-crossing curriculum work. Then introduce the embedding-based method as the principled alternative.

The data analyzed here is already the evidence for both framings.
