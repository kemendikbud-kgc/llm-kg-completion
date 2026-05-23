# Bab 4 Dev — Methodology Diagrams (Mermaid)

Three flowchart diagrams to drop into the **Bab 4 Dev** tab of the thesis doc.
All render natively in Google Docs (paste as text → it becomes editable),
in GitHub, in JupyterLab/VS Code, and in any modern Markdown viewer.

For the live Google Doc: paste as a code block, then insert a rendered PNG
exported from [mermaid.live](https://mermaid.live) underneath. Caption the
PNG with `Gambar 3.X` and reference it in the prose.

---

## Gambar 3.A — Pipeline 5 Tahap (overview)

Top-down flowchart of the full pipeline from PDF input to expert-validated
knowledge graph. Replaces the table at the top of Bab 4 Dev with a visual.

```mermaid
flowchart TB
    PDF[PDF buku siswa<br/>+ buku guru] --> ING[Tahap 1: Ingestion]
    ING -->|teks per halaman<br/>+ ToC + glosarium<br/>+ materi pokok| EX[Tahap 2: Extraction]
    EX -->|JSON konsep<br/>+ relasi within-chapter<br/>+ chapter_relations| GC[Tahap 3: Graph Construction]
    GC -->|Neo4j graph:<br/>Grade -> Chapter<br/>-> Subtopic -> Concept| KGC[Tahap 4: KGC]
    KGC -->|LINTAS_BUKU_* edges<br/>lintas-disiplin| EV[Tahap 5: Evaluation]
    EV --> METRIK[Structural Metrics<br/>ADC, Density,<br/>Modularity, TRR]
    EV --> PAKAR[Expert Validation<br/>via KG Review App<br/>Precision/Recall/F1, kappa]

    classDef stage fill:#e7f0ff,stroke:#2056ae,stroke-width:1.5px,color:#0d2b5b
    classDef artifact fill:#fff8e1,stroke:#a86e00,color:#5a3a00
    classDef eval fill:#e8f5e9,stroke:#2e7d32,color:#1b3a1f

    class ING,EX,GC,KGC,EV stage
    class PDF,METRIK,PAKAR artifact
```

---

## Gambar 3.B — Strategi MERGE Tiga-Pass (Tahap 3 detail)

Detailed view of Tahap 3 — explains the Concept vs ConceptTarget split and
the per-pass guarantees (idempotency, forward-reference handling, lazy
materialization). The prose in Bab 4 Dev currently describes this in 4
paragraphs; the diagram makes the algorithm visually obvious.

```mermaid
flowchart TB
    INPUT[JSON ekstraksi Tahap 2<br/>3 buku x N chapter] --> P1

    subgraph Pass1[Pass 1: Node ingestion + tulang punggung]
        P1[MERGE Grade, Chapter,<br/>Subtopic, Concept nodes]
        P1 --> P1A[Struktural relations:<br/>HAS_CHAPTER, HAS_SUBTOPIC,<br/>HAS_CONCEPT, NEXT_CHAPTER]
        P1A -.-> P1B[(Idempotent:<br/>kunci name+grade<br/>shared lintas-dokumen)]
    end

    Pass1 --> P2D{Target in<br/>concept set<br/>buku saat ini?}

    subgraph Pass2[Pass 2: Intra-book typed relations]
        P2D -->|ya| P2A[Concept -> Concept<br/>edge]
        P2D -->|tidak| P2B[Concept -> ConceptTarget<br/>edge - placeholder]
        P2A & P2B -.-> P2C[(_safe_rel:<br/>normalisasi tipe<br/>ke Cypher syntax)]
    end

    Pass2 --> P3D{target_book<br/>!= source_book?}

    subgraph Pass3[Pass 3: Cross-book LINTAS_BUKU_*]
        P3D -->|ya| P3A[MERGE Concept di<br/>scope grade tujuan]
        P3A --> P3B[LINTAS_BUKU_RELTYPE<br/>edge dengan prefix]
        P3B -.-> P3C[(Lazy materialization:<br/>buat node target<br/>jika belum ada)]
    end

    Pass3 --> OUT[Neo4j graph<br/>siap untuk Tahap 4]

    classDef pass fill:#fff3e0,stroke:#bf5c00,color:#5a2c00
    classDef decision fill:#fce4ec,stroke:#ad1457,color:#560027
    classDef note fill:#f5f5f5,stroke:#666,stroke-dasharray:3 3,color:#333

    class P1,P1A,P2A,P2B,P3A,P3B pass
    class P2D,P3D decision
    class P1B,P2C,P3C note
```

---

## Gambar 3.C — Pipeline KGC (Tahap 4 detail)

Detailed view of Tahap 4 — the thesis's core methodological contribution.
Shows embedding → vector index → ANN retrieval → pruning → LLM-as-classifier
with closed vocabulary → writeback. Includes the KONTEKS GRAF block fed to
the classifier as evidence (this is the differentiator from prior LLM-only
completion methods).

```mermaid
flowchart LR
    NODE[Concept dengan<br/>description, grade,<br/>materi_pokok_ref] --> EMB[Embed:<br/>name + description<br/>+ materi_pokok_ref<br/>+ grade]
    EMB --> VEC[Store as<br/>Concept.embedding<br/>+ vector index<br/>cosine, HNSW]
    VEC --> ANN[ANN top-k<br/>per Concept]

    ANN --> FILTER{Pruning filters}
    FILTER -->|cross-grade only| F1
    FILTER -->|skip existing<br/>typed edges| F1
    FILTER -->|dedupe<br/>undirected pairs| F1[Candidate pairs<br/>sim >= threshold]

    F1 --> CTX[Build KONTEKS GRAF:<br/>parent Bab<br/>+ typed out-edges<br/>+ shared neighbors]

    CTX --> LLM[LLM classifier<br/>Gemini 2.5 Flash<br/>temperature=0.2<br/>response_schema enum]

    LLM --> VOCAB{Closed vocab<br/>5 LINTAS_BUKU_*<br/>atau NONE}
    VOCAB -->|valid + conf >= 0.7| WB[Write LINTAS_BUKU_*<br/>edge to Neo4j]
    VOCAB -->|NONE / low conf| DROP[Drop pair]

    WB --> DUMP[Stage to<br/>lintas_buku_edges.json<br/>friend-llm format]
    DUMP --> REPLAY[replay_completion.py<br/>MERGE ke Neo4j]

    classDef step fill:#e3f2fd,stroke:#1565c0,color:#0a3266
    classDef decision fill:#fce4ec,stroke:#ad1457,color:#560027
    classDef output fill:#e8f5e9,stroke:#2e7d32,color:#1b3a1f
    classDef drop fill:#fafafa,stroke:#999,color:#666,stroke-dasharray:3 3

    class NODE,EMB,VEC,ANN,F1,CTX,LLM step
    class FILTER,VOCAB decision
    class WB,DUMP,REPLAY output
    class DROP drop
```

---

## How to use these in the thesis

1. **Inline preview**: paste each ```mermaid``` block directly into the Google
   Doc. Docs renders it as plain text in monospace — preserves source for any
   re-editing.

2. **Rendered figures**: open [mermaid.live](https://mermaid.live), paste the
   diagram, export as PNG (transparent background, 2x scale for print). Insert
   the PNG as `Gambar 3.A` / `3.B` / `3.C` directly under the source block.

3. **Caption convention** (match existing thesis style):
   - `Gambar 3.A Pipeline 5 Tahap KG Construction & Completion`
   - `Gambar 3.B Strategi MERGE Tiga-Pass pada Tahap Konstruksi Graf`
   - `Gambar 3.C Detail Pipeline Knowledge Graph Completion (KGC)`

4. **Reference in prose**: replace passages like *"Sistem dibangun dengan
   arsitektur pipeline 5 tahap..."* with `... lihat Gambar 3.A`.

---

## Editing notes

- Mermaid syntax intentionally avoids special characters that confuse Google
  Docs paste (no `→`, no emoji — replaced with `->` and ASCII).
- Colors use a 3-class palette: stage/process (blue), decision/branch (pink),
  output/artifact (green/yellow). Re-styleable via the `classDef` lines at
  the bottom of each diagram.
- If a diagram exceeds page width when rendered, the `flowchart TB` (top-bottom)
  vs `flowchart LR` (left-right) directive in the first line controls aspect.
