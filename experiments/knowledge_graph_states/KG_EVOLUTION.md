---
title: KG Extraction State Evolution
date: 2026-05-25
tags:
  - knowledge-graph
  - extraction
  - evolution
---

# KG Extraction State Evolution

## Flow

```mermaid
graph TD
    V1["<b>v1 — extraction</b><br/>323 concepts | 557 relations<br/><i>LLM extraction from books</i>"]
    V2["<b>v2 — reviewed</b><br/>350 concepts | 581 relations<br/><i>Expert-reviewed baseline</i>"]
    V3["<b>v3 — toc-gap-byCC</b><br/>358 concepts | 596 relations<br/><i>+ Claude Code ToC gap analysis</i>"]
    V4["<b>v4 — validated-byCC</b><br/>363 concepts | 612 relations<br/><i>+ expert-fisika-4 validation</i>"]

    V1 -->|"+27 concepts (expert-kimia-6)<br/>−3 relations (dropped as wrong)<br/>+expert_review annotations"| V2
    V2 -->|"+8 concepts (CC)<br/>+15 relations<br/>5 Fisika + 3 Kimia from ToC scan"| V3
    V3 -->|"+5 concepts (expert-fisika-4)<br/>+16 relations<br/>3 CC additions independently validated"| V4

    style V1 fill:#e8e8e8,stroke:#666
    style V2 fill:#d4edda,stroke:#28a745
    style V3 fill:#cce5ff,stroke:#007bff
    style V4 fill:#fff3cd,stroke:#ffc107
```

## Per-Subject Breakdown

```mermaid
graph LR
    subgraph Biologi
        B1["v1: 85c / 151r"] --> B2["v2: 85c / 151r"] --> B3["v3: 85c / 151r"] --> B4["v4: 85c / 151r"]
    end
    subgraph Fisika
        F1["v1: 124c / 240r"] --> F2["v2: 124c / 237r<br/><i>−3 dropped</i>"] --> F3["v3: 129c / 246r<br/><i>+5 CC</i>"] --> F4["v4: 134c / 262r<br/><i>+5 expert</i>"]
    end
    subgraph Kimia
        K1["v1: 114c / 166r"] --> K2["v2: 141c / 193r<br/><i>+27 expert</i>"] --> K3["v3: 144c / 199r<br/><i>+3 CC</i>"] --> K4["v4: 144c / 199r"]
    end

    style B1 fill:#e8e8e8
    style B2 fill:#d4edda
    style B3 fill:#cce5ff
    style B4 fill:#fff3cd
    style F1 fill:#e8e8e8
    style F2 fill:#d4edda
    style F3 fill:#cce5ff
    style F4 fill:#fff3cd
    style K1 fill:#e8e8e8
    style K2 fill:#d4edda
    style K3 fill:#cce5ff
    style K4 fill:#fff3cd
```

## Delta Summary

| Version | Source | Concepts | Relations | Key Action |
|---------|--------|----------|-----------|------------|
| **v1** | LLM pipeline | 323 | 557 | Yhoga's extraction from PDF books |
| **v2** | + expert review | 350 (+27) | 581 (+24) | expert-kimia-6 added 27; 3 Fisika dropped as wrong |
| **v3** | + Claude Code | 358 (+8) | 596 (+15) | ToC-vs-KG gap scan: Inframerah, Relativitas x4, Stoikiometri, Perbandingan Sel, Mobil Listrik |
| **v4** | + expert-fisika-4 | 363 (+5) | 612 (+16) | Muatan Kapasitor, Alat Ukur, Efisiensi Trafo, Nilai Efektif AC, Dualisme Gelombang-Partikel + 6 formula relations |

## Provenance Composition (v4)

```mermaid
pie title Concept Provenance (363 total)
    "Original extraction" : 323
    "expert-kimia-6 (v2)" : 27
    "Claude Code ToC-gap (v3)" : 8
    "expert-fisika-4 (v4)" : 5
```

## Validation Status

| Reviewer | Subject | Triples Rated | Correct | Issues |
|----------|---------|---------------|---------|--------|
| expert-biologi-1 | Bio | partial | -- | incorporated in v2 |
| expert-biologi-6 | Bio | partial | -- | incorporated in v2 |
| **expert-biologi-4** | Bio | **151/151** | **100%** | 2 cosmetic comments |
| expert-fisika-6 | Fisika | partial | -- | incorporated in v2 |
| **expert-fisika-4** | Fisika | **240/240** | **99.6%** | 1 "missing" (description fix), 15 new triples proposed |
| expert-kimia-6 | Kimia | partial | -- | incorporated in v2, proposed 27 additions |
| expert-fisika-2-kimia | Kimia | partial | -- | incorporated in v2 |

## CC Validation Highlight

3 of 5 Claude Code ToC-gap additions were **independently proposed** by expert-fisika-4 (who reviewed the v1 extraction without seeing CC's work):

- Pemanfaatan Inframerah
- Dilatasi Waktu
- Penambahan Kecepatan Relativistik
