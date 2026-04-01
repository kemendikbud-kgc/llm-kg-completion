# Expert Validation Pipeline for LLM-Extracted Knowledge Graph

## Overview

- **Participants:** 3 teachers (1 Fisika, 1 Kimia, 1 Biologi)
- **Duration:** ~60-90 minutes per teacher
- **Format:** Semi-structured interview + structured validation form + Likert questionnaire
- **Output:** Precision, Recall, F1, Likert scores, qualitative triangulation

---

## Evaluation Philosophy

### "Fitness for Use" Principle

Based on Zhang & Xiao (2024), this evaluation follows the **"Fitness for Use"** principle: results should be practically actionable for teachers, not just measure intrinsic data accuracy.

We prioritize:
- **Concepts most relevant to curriculum** — weighted by teaching frequency
- **Relations teachers actually use** — prerequisite chains, supporting concepts
- **Format accessible to non-technical evaluators** — natural language, not graph notation

### Why Natural Language Statements?

| Format | Cognitive Load | Error Isolation | Best For |
|--------|---------------|-----------------|----------|
| Raw triples (A, REL, B) | High | Medium | Technical users |
| Graph visualization | High | Low | Overview only |
| **Natural language statements** | **Low** | **High** | **Domain experts ✓** |

---

## Phase 1: Briefing (10 minutes)

**Goal:** Orient the teacher so they understand what they're evaluating.

1. Explain the project: "Kami membangun Knowledge Graph otomatis dari buku teks menggunakan AI untuk memetakan konsep dan keterkaitannya"
2. Show 1 full-graph screenshot (for context, not evaluation)
3. Show 1 per-Bab subgraph screenshot from their subject — walk through nodes and edges
4. Explain terminology: Konsep, SubKonsep, Relasi (MENYEBABKAN, BERGANTUNG_PADA, etc.)
5. Clarify: "Kami ingin tahu apakah hasil ekstraksi AI ini akurat dan berguna menurut pengalaman Bapak/Ibu mengajar"

**Do NOT ask them to evaluate anything yet.**

---

## Phase 2: Qualitative Interview — Semi-Structured (20-30 minutes)

**Goal:** Gather qualitative insights about curriculum structure from the teacher's perspective, BEFORE showing KG details (to avoid anchoring bias).

**Method:** Semi-structured interview, recorded (with consent) or noted.

### 2A. Metrik Struktural (Interconnectedness)

Maps to: Average Degree Centrality, Graph Density, Modularity

| No | Pertanyaan |
|----|-----------|
| 1 | Menurut Bapak/Ibu, apakah konsep-konsep dalam materi sains saling terhubung atau diajarkan secara terpisah? Bisa beri contoh? |
| 2 | Seberapa sering Bapak/Ibu mengaitkan satu topik dengan topik lain saat mengajar? |
| 3 | Apakah siswa biasanya memahami hubungan antar konsep (misalnya energi dengan gaya)? |
| 4 | Apakah ada topik yang terasa berdiri sendiri tanpa kaitan dengan topik lain? |
| 5 | Dalam perencanaan pembelajaran, apakah hubungan antar materi sudah terlihat jelas? |

### 2B. Metrik Ekstraksi (Description Quality)

Maps to: Description Completeness, Empty SubKonsep Rate

| No | Pertanyaan |
|----|-----------|
| 1 | Apakah semua konsep yang diajarkan memiliki penjelasan yang cukup jelas bagi siswa? |
| 2 | Apakah ada konsep yang sering membuat siswa bingung karena kurang penjelasan? |
| 3 | Apakah setiap konsep utama sudah dipecah menjadi sub-konsep yang mudah dipahami? |
| 4 | Apakah ada materi yang terlalu umum tanpa penjabaran detail? |
| 5 | Seberapa penting memberikan contoh atau deskripsi pada setiap konsep? |

### 2C. Metrik Hubungan (Relationship Quality)

Maps to: Typed Relation Ratio, Prerequisite Chain Length

| No | Pertanyaan |
|----|-----------|
| 1 | Saat menjelaskan hubungan antar konsep, apakah Bapak/Ibu menjelaskan jenis hubungan tersebut (misalnya sebab-akibat atau bagian dari)? |
| 2 | Apakah siswa memahami urutan belajar konsep (mana yang harus dipahami terlebih dahulu)? |
| 3 | Apakah ada materi yang membutuhkan pemahaman berlapis (konsep prasyarat)? |
| 4 | Apakah hubungan antar materi sudah cukup jelas atau masih membingungkan? |
| 5 | Apakah ada keterkaitan antar mata pelajaran (misalnya sains dengan matematika)? |

---

## Data Presentation Format

### Principle
Present KG data as **natural language statements** rather than raw graph structures or triple notation. This reduces cognitive load and allows teachers to focus on content correctness rather than graph interpretation.

### Statement Types

**Atomic Statements** (for Phase 3 validation):
- **Concept:** "Enzim adalah protein yang berfungsi sebagai katalis dalam reaksi biokimia."
- **Relation:** "Enzim memiliki sifat Spesifisitas."
- **SubKonsep:** "Lock and Key adalah bagian dari konsep Enzim."

**Chain Statements** (for Phase 4 Likert only, 3-5 items):
- "Untuk memahami Respirasi Sel, urutan belajar yang tepat adalah: Mitokondria → Glikolisis → Siklus Krebs → Daur Elektron"

### Why Atomic Statements for Validation?

| Aspect | Atomic | Long Chain |
|--------|--------|------------|
| Cognitive load | Low (~5-10 sec/item) | High (~30-60 sec/item) |
| Error isolation | Easy to pinpoint | Ambiguous which part is wrong |
| Metrics | Clean precision/recall | Difficult to score |
| Throughput | 30-50 items | 5-10 items in same time |

---

## Phase 3: Structured Validation — VALIDASI AKURASI (20-30 minutes)

**Goal:** Quantitative evaluation of KG correctness.

**Method:** Teacher fills a printed form or Google Sheet with sampled KG data.

### Task A: Ketepatan Konsep (Precision)

Present 30-50 randomly sampled Konsep statements (stratified by Bab).

| No | Bab | Pernyataan | Benar | Salah | Tidak Yakin | Catatan |
|----|-----|------------|-------|-------|-------------|---------|
| 1 | Bab 3 | "Enzim adalah protein yang berfungsi sebagai katalis dalam reaksi biokimia" | ○ | ○ | ○ | |
| 2 | Bab 3 | "Suhu optimum kerja enzim adalah 37°C untuk enzim manusia" | ○ | ○ | ○ | |
| ... | ... | ... | | | | |

**Note:** "Tidak Yakin" allows distinguishing genuine uncertainty from ambiguous statements.

```
Precision = jumlah "Benar" / total sampel
Uncertainty Rate = jumlah "Tidak Yakin" / total sampel
```

### Task B: Ketepatan Relasi (Relation Accuracy)

Present 20-30 randomly sampled relation statements (stratified by relation type).

| No | Tipe | Pernyataan Hubungan | Benar | Salah | Tidak Yakin | Catatan |
|----|------|---------------------|-------|-------|-------------|---------|
| 1 | Prasyarat | "Untuk memahami Hukum Newton II, perlu memahami Konsep Gaya terlebih dahulu" | ○ | ○ | ○ | |
| 2 | Supports | "Konsep Vektor mendukung pemahaman tentang Hukum Newton" | ○ | ○ | ○ | |
| 3 | Analogous | "Gaya gravitasi memiliki kesamaan dengan Gaya listrik" | ○ | ○ | ○ | |
| ... | ... | ... | | | | |

```
Relation Precision = jumlah "Benar" / total sampel
Type Accuracy = per-type breakdown (which relation types are most/least accurate)
Uncertainty Rate = jumlah "Tidak Yakin" / total sampel
```

### Task C: Kelengkapan (Recall)

For each Bab, show extracted Konsep list. Teacher writes missing ones.

| Bab | Konsep yang Diekstrak | Konsep yang Hilang (isi manual) |
|-----|----------------------|-------------------------------|
| ... | ... | (guru mengisi) |

```
Recall = konsep diekstrak / (konsep diekstrak + konsep hilang)
F1 = 2 * (Precision * Recall) / (Precision + Recall)
```

---

## Phase 4: KG Review + Likert Questionnaire (10-15 minutes)

**Goal:** Measure perceived usefulness after teacher has seen the KG in detail.

### Show:
- 3-4 per-Bab subgraph screenshots (cleanly laid out, labeled)
- Highlight cross-chapter connections and SIMILAR_TO edges

### Likert Scale (1-5: Sangat Tidak Setuju ... Sangat Setuju)

**Akurasi**
1. Konsep yang diekstrak sesuai dengan isi buku teks
2. Hubungan antar konsep menggambarkan keterkaitan yang benar
3. Hierarki Bab - Konsep - SubKonsep sudah tepat

**Kelengkapan**
4. Konsep-konsep penting dalam buku sudah tercakup
5. Tidak ada hubungan penting yang hilang

**Kegunaan**
6. KG ini berguna untuk memahami struktur kurikulum
7. KG ini dapat membantu perencanaan pembelajaran
8. KG ini dapat mengidentifikasi keterkaitan antar-bab yang tidak langsung terlihat

**Efisiensi**
9. Pembuatan KG otomatis lebih efisien dibandingkan pemetaan manual
10. Hasil KG otomatis mendekati kualitas pemetaan manual oleh guru

```
Per-dimensi: Mean +/- SD
Overall: Mean +/- SD (semua 10 item)
```

**Open-ended:**
11. Apa kelebihan utama KG ini?
12. Apa yang perlu diperbaiki?

---

## Phase 5: Analysis & Triangulation (Post-Interview)

### 5A. Quantitative Results Table

| Metrik | Fisika | Kimia | Biologi |
|--------|--------|-------|---------|
| Precision (Task A) | | | |
| Recall (Task C) | | | |
| F1 | | | |
| Relation Precision (Task B) | | | |
| Type Accuracy (Task B) | | | |
| Likert Akurasi (mean+/-SD) | | | |
| Likert Kelengkapan (mean+/-SD) | | | |
| Likert Kegunaan (mean+/-SD) | | | |
| Likert Efisiensi (mean+/-SD) | | | |

### 5B. Graph Metrics (from Neo4j)

| Metrik | Fisika | Kimia | Biologi |
|--------|--------|-------|---------|
| Total Nodes | | | |
| Total Edges | | | |
| Avg Degree Centrality | | | |
| Graph Density | | | |
| Modularity | | | |
| Typed Relation Ratio | | | |
| Max Prerequisite Chain | | | |
| Description Completeness | | | |
| Empty SubKonsep Rate | | | |

### 5C. Triangulation Matrix

Cross-reference qualitative answers with quantitative metrics:

| Interview Finding | Related Metric | Metric Value | Aligned? |
|---|---|---|---|
| Example: "Fisika banyak topik berdiri sendiri" | Graph Density (Fisika) | 0.03 (low) | Yes |
| Example: "Biologi sangat terhubung" | ADC (Biologi) | 0.45 (high) | Yes |

---

## Summary of All Metrics

| Category | Metric | Method | Source |
|----------|--------|--------|--------|
| **Accuracy** | Precision | Task A (binary) | Teacher form |
| | Recall | Task C (missing concepts) | Teacher form |
| | F1 | Computed | P & R |
| | Relation Precision | Task B (binary) | Teacher form |
| | Type Accuracy | Task B (binary) | Teacher form |
| **Perception** | Likert (4 dimensions) | 5-point scale | Teacher questionnaire |
| **Graph Quality** | ADC, Density, Modularity | Computed | Neo4j |
| | Typed Relation Ratio | Computed | Neo4j |
| | Prereq Chain Length | Computed | Neo4j |
| | Desc Completeness | Computed | Neo4j |
| **Qualitative** | Interview themes | Thematic coding | Interview notes |
| **Triangulation** | Alignment matrix | Cross-reference | All sources |

---

## Limitations to Acknowledge

- Single evaluator per subject (no inter-rater reliability / Cohen's Kappa)
- Purposive sampling of teachers (not random)
- Likert with n=1 per subject — descriptive statistics only, no inferential tests
- Teacher may be anchored by seeing the KG before filling Likert

---

## References

- Zhang, Y., & Xiao, G. (2024). A novel customizing knowledge graph evaluation method for incorporating user needs. *Scientific Reports*, 14, 9594. https://doi.org/10.1038/s41598-024-60004-x
- Carriero, V. A., et al. (2024). Human Evaluation of Procedural Knowledge Graph Extraction from Text with Large Language Models. *arXiv:2412.03589*. https://arxiv.org/abs/2412.03589
