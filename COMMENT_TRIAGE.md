# Thesis Doc — Comment Triage & Action Plan

Source: "TA Cleanup Copy" (`1NUFWP1JHmpH...`). Pulled 2026-06-01.
**100 comments total — 29 solved (✅ reply / resolved) — 71 open.**

Workflow agreed: **draft proposed text → you approve → I apply via `batchUpdate`.** Nothing applied yet.

---

## A. LECTURER — Siti Aminah (the priority; ~31 open)

### A1. Mechanical / style (low-risk, fast, apply in one batch)
| # | Anchor | Comment | Proposed fix |
|---|--------|---------|--------------|
| 11 | `-0,5` | "perbaiki tulisan angkanya" | The phrase "nilai mendekati -1, atau -0,5" is muddled. Rewrite: "…dan nilai mendekati −1 menunjukkan kedua vektor berlawanan arah (makna berkebalikan)." Drop the stray "atau −0,5"; use proper minus sign (−). |
| 16 | `Sangat` | "hiperbola, hindari" | "relasi yang **sangat penting**" → "relasi yang **penting**" (remove intensifier + lowercase). |
| 34 | `Knowledge Graph (KG)` | don't re-expand acronym | Find repeat expansions after first definition; replace with "KG". |
| 41 | `M` | "tidak perlu kapital" | Lowercase the flagged word. |
| 46 | `embedding` | italic all foreign terms | Italicize *embedding* and sweep all English terms (long-tail, reasoning, encoder, etc.). |
| 47 | `Meskipun` | "paragraf baru" | Insert paragraph break before "Meskipun". |
| 57 | `Desain Kurikulum dan Pemetaan Konsep` | why title-case? | Sentence-case: "Desain kurikulum dan pemetaan konsep". |
| 58 | `reasoning` | italic + check all | Italicize *reasoning*; same sweep as #46. |

### A2. Define / clarify a term (need a sentence of definition)
| # | Anchor | Comment | Proposed approach |
|---|--------|---------|-------------------|
| 13 | `entitas` | "sumber?" | Add citation for the entity-count claim (likely a KG survey, e.g. Ji et al. 2021). **Need: which source.** |
| 14 | `kelengkapan` | "kelengkapan intrinsik maksudnya apa?" | Define or drop "intrinsik". Propose: "kelengkapan (proporsi relasi wajib kurikulum yang berhasil direpresentasikan)". |
| 15 | `konsistensi` | "maksudnya apa?" | Define: "konsistensi (tidak adanya relasi yang saling bertentangan dalam graf)". |
| 19 | `faktualitas` | "what is the meaning here?" | Define inline: "faktualitas (kebenaran faktual relasi yang dihasilkan terhadap materi sumber)". |
| 31 | `ontologi` | define (idem #30, which is ✅) | Mirror the definition already accepted at #30. |
| 36 | `kelangkaan data` | "data SMA melimpah, kenapa langka?" | Clarify: kelangkaan bukan pada teks sumber, tapi pada **relasi eksplisit antar-konsep** (graf awal sangat sparse). Reword the sentence. |
| 45 | `long-tail` | define at first use | Move the long-tail definition to its first occurrence (see #26). |
| 52 | `informasi struktural` | "apa maksudnya?" | Define: "informasi struktural (pola konektivitas antar-node dalam graf, bukan makna teksnya)". |

### A3. Explain / rewrite (substantive)
| # | Anchor | Comment | Proposed approach |
|---|--------|---------|-------------------|
| 17 | KICGPT sentence | "perlu diagram" | Add a figure illustrating KICGPT (KGC pipeline + LLM ICL). **Need: make diagram.** |
| 21 | `arsitektur KGC modern…` | "ANN muncul tanpa transisi" + **duplicated sentence** | Sentence is literally repeated twice — delete the dup, and add a bridging clause explaining *why* vector DB + ANN is needed before naming it. |
| 23 | `Dengan reformulasi ini…` | "kalimat panjang" | Split the long sentence into two. |
| 25 | `Distribusi topik…` | "kalimat panjang" | Split. |
| 26 | `Keterbatasan… long-tail` | define long-tail at first use | Insert definition here (resolves #45). |
| 38 | `Manfaat Penelitian` (1.4) | "fully AI-generated, bertele-tele" | Rewrite subbab 1.4 concise, in own voice, no repetition. **Need your voice/approval.** |
| 48 | `Lebih dari itu…` | "bahasa terjemahan, paraphrase + definisikan ICL" | Paraphrase naturally + add 1-line ICL definition. |
| 49 | `encoder maupun generator` | "muncul tiba-tiba, jelaskan" | Add a clause distinguishing encoder vs generator LLM architectures (resolves #4, #5 from Fadrian too). |
| 53 | `penurunan performa drastis` | "jelaskan lebih lanjut" | Add why structural embeddings degrade on long-tail (few training triples → poor representation). |

### A4. "sumber?" — needs citations (data dependent on your refs)
| # | Anchor | Note |
|---|--------|------|
| 24 | `Hal ini berarti metode embedding konvensional…` | needs source |
| 27 | `Pada fase awal perkembangannya, KGC…` | needs source |

> Several A-items show as "anchor text no longer in doc" — those comments were left on text you've since edited; they may be **orphaned** and can be resolved/dismissed after we verify the current wording.

---

## B. TEAMMATES — Tegar Wahyu & Fadrian Yhoga (open)
- **4, 5** (Fadrian: `generator`/`encoder`) → resolved together with A3 #49.
- **3** (Fadrian: "holistik dan meaningful learning") → note: lecturer #44 says *drop* "holistik". Reconcile — likely **remove**, don't add.
- **2** (Tegar: TOC vs konten classification "diperjelas") → expand the method paragraph in Bab 3.
- **9** (Tegar: 4-step pipeline → "masukin ke bab 2") → move the pipeline list to Bab 2.
- **65** (Tegar: "fiksasi" on 4.1.4 heading) → finalize section title.
- **82, 83, 84** (Tegar): F1/precision/recall + Cohen Kappa already in metrics → de-duplicate; move Cypher to lampiran, remove formulas.
- **90** (Tegar): excalidraw link → diagram to be drawn.
- **96** (Fadrian): reviewer-criteria fallback note → delete after finalizing.

## C. YOUR OWN TODO MARKERS — Soros / Soros Febriano (open, not "lecturer")
Grouped by type:
- **Recall formula [1]** — *broken (yields >1)*. Fix: add "Konsep Sebagian Benar" to denominator and justify/remove the 0.5 weight. Tegar concurs. **High priority, technical.**
- **Overclaim [0]** — "seluruh konsep" → "konsep yang teridentifikasi" (can't claim the full ideal set).
- **Figures/placeholders [6,7,8,62]** — replace first-attempt visualizations + UMAP caption.
- **Numbering [59,93]** — fix "ngasal" section numbers; make figure numbering dynamic.
- **Cross-book scope [63]** — "Kita lintas buku doang" → drop intra-buku threshold mention.
- **Code blocks [68,69,70,71,72]** — render Cypher inside code blocks.
- **Integrate/relocate [60,61,84]** — merge 4.2.3.1 with expert-validation triple ratings; relocate param-sweep image.
- **References needed [74]** — context engineering, in-context learning, LLM params (batch, top-k, temperature).
- **Recheck data [88,92,94,98]** — verify numbers (0,713 etc.), relation-type table, ontology schema, Cohen's Kappa source.
- **Prose review [89]** — "Straight from Opus" pembahasan kualitatif → rewrite in own voice.
- **Em-dashes [87]** — sweep and remove/replace em-dashes.
- **Excel-linked tables [75,76]** — data may still change; revisit last.
- **Verify prompt [77]** — @Fadrian to confirm prompt used.

---

## Suggested execution order
1. **A1 mechanical sweep** (italics, capitals, hyperbole, dup sentence) — one `batchUpdate`, low risk.
2. **A2 definitions** — short inserts, I draft text for your OK.
3. **Recall formula [1] + overclaim [0]** — technical, high value.
4. **A3 rewrites + 1.4 [38]** — needs your voice; I draft, you edit.
5. **A4 + C citations [24,27,74]** — you supply refs.
6. **Figures/diagrams [17,90,6-8,62]** — separate task (need drawing).
7. Teammate cleanups (B) + remaining C recheck items.
