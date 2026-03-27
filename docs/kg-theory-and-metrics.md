# Knowledge Graph: Theory, Construction, and Evaluation

## Table of Contents
1. [Introduction to Knowledge Graphs](#1-introduction-to-knowledge-graphs)
2. [Knowledge Graph Representation](#2-knowledge-graph-representation)
3. [Knowledge Graph Construction](#3-knowledge-graph-construction)
4. [Knowledge Graph Completion](#4-knowledge-graph-completion)
5. [Knowledge Graph Metrics](#5-knowledge-graph-metrics)
6. [Human Evaluation Methods](#6-human-evaluation-methods)
7. [Application to Curriculum Analysis](#7-application-to-curriculum-analysis)

---

## 1. Introduction to Knowledge Graphs

### 1.1 Definition

A **Knowledge Graph (KG)** is a directed, labeled multi-relational graph that represents knowledge as a network of entities and their relationships. Formally, a KG is defined as:

$$G = (E, R, T)$$

Where:
- $E = \{e_1, e_2, ..., e_{|E|}\}$ is the set of entities (nodes)
- $R = \{r_1, r_2, ..., r_{|R|}\}$ is the set of relations (edge types)
- $T \subseteq E \times R \times E$ is the set of triples (edges)

Each triple $(h, r, t) \in T$ represents a fact: head entity $h$ is related to tail entity $t$ via relation $r$.

### 1.2 Historical Context

| Year | Milestone |
|------|-----------|
| 2001 | Berners-Lee introduces Semantic Web vision |
| 2012 | Google announces Knowledge Graph |
| 2013 | Freebase knowledge base released |
| 2014 | Wikidata launches |
| 2016 | DBpedia, YAGO become standard benchmarks |

### 1.3 Types of Knowledge Graphs

| Type | Description | Examples |
|------|-------------|----------|
| **Encyclopedic** | General world knowledge | Wikidata, DBpedia, Freebase |
| **Domain-Specific** | Specialized domain knowledge | UMLS (medical), GeoNames (geographic) |
| **Enterprise** | Business/organizational knowledge | Product catalogs, customer data |
| **Educational** | Learning content and curricula | Curriculum ontologies, learning graphs |

---

## 2. Knowledge Graph Representation

### 2.1 Ontological Structure

Knowledge graphs are typically organized using an **ontology** that defines:

1. **Classes (TBox)** - Concept categories
2. **Properties (ABox)** - Instance attributes and relations
3. **Axioms** - Logical constraints

```
┌─────────────────────────────────────────────────────────────┐
│                    ONTOLOGY LAYER                           │
├─────────────────────────────────────────────────────────────┤
│  TBox (Terminological)     │  ABox (Assertional)           │
│  ─────────────────────     │  ──────────────────           │
│  Class: Konsep             │  Instance: HukumNewton         │
│  Class: SubKonsep          │  Instance: GayaGesek           │
│  Property: isPrerequisiteOf│  Triple: (HukumNewton,        │
│  Property: hasSubKonsep    │    isPrerequisiteOf, GayaGesek)│
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Graph Data Models

#### RDF (Resource Description Framework)
Standard model for data interchange on the Web:

```turtle
@prefix ex: <http://example.org/curriculum/> .

ex:HukumNewton a ex:Konsep ;
    ex:name "Hukum Newton I" ;
    ex:description "Hukum kelembaman..." ;
    ex:bloomLevel "understand" ;
    ex:isPrerequisiteOf ex:GayaGesek .
```

#### Property Graph Model
Used by Neo4j, more flexible for complex relationships:

```
(:Konsep {name: "Hukum Newton", bloom_level: "understand"})
  -[:isPrerequisiteOf]->(:Konsep {name: "Gaya Gesek"})
```

### 2.3 Schema Design Patterns

| Pattern | Description | Use Case |
|---------|-------------|----------|
| **Hierarchical** | Tree-like taxonomy | Curriculum → Bab → SubBab → Konsep |
| **Network** | Interconnected concepts | Cross-references, prerequisites |
| **Hybrid** | Hierarchy + lateral links | Educational KGs (this thesis) |

---

## 3. Knowledge Graph Construction

### 3.1 Construction Pipeline

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Data       │    │   Entity     │    │  Relation    │    │   Quality    │
│   Sources    │───▶│  Extraction  │───▶│  Extraction  │───▶│   Control    │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
      │                    │                    │                    │
      ▼                    ▼                    ▼                    ▼
  PDF/Text           NER/NER+        Pattern/ML/LLM           Validation
  Databases          Classification   Classification           Deduplication
  APIs               Linking          Knowledge Base           Fusion
```

### 3.2 Entity Extraction Methods

#### A. Named Entity Recognition (NER)
Traditional NLP approach using:
- Rule-based systems (gazetteers, patterns)
- Statistical models (CRF, HMM)
- Deep learning (BiLSTM-CRF, BERT-based)

#### B. LLM-based Extraction (This Thesis)
Using Large Language Models with structured output:

```python
# Prompt-based extraction with Pydantic schema
class KonsepExtraction(BaseModel):
    konsep: List[Konsep]

class Konsep(BaseModel):
    name: str
    description: str
    bloom_level: Literal["remember", "understand", "apply",
                         "analyze", "evaluate", "create"]
    sub_konsep: List[SubKonsep]
```

**Advantages of LLM-based extraction:**
- Zero/few-shot capability
- Contextual understanding
- Structured output generation
- Domain adaptation via prompting

### 3.3 Relation Extraction Methods

| Method | Description | Precision | Recall |
|--------|-------------|-----------|--------|
| **Pattern-based** | Regex/dependency patterns | High | Low |
| **Supervised ML** | Classifiers on labeled data | Medium | Medium |
| **Distant supervision** | Align with existing KB | Low | High |
| **LLM-based** | Prompt with relation schema | High | Medium-High |

---

## 4. Knowledge Graph Completion

### 4.1 Problem Definition

Given an incomplete KG $G = (E, R, T)$, predict missing triples:

$$\hat{T} = \{(h, r, t) : (h, r, t) \notin T \land \text{should exist}\}$$

### 4.2 Completion Approaches

#### A. Embedding-Based Methods (KGE)

**Translational Models:**
- **TransE**: $\|h + r - t\| \approx 0$
- **TransH**: Projection to relation-specific hyperplane
- **TransR**: Entity and relation spaces separated

**Semantic Matching Models:**
- **DistMult**: Bilinear diagonal form
- **ComplEx**: Complex-valued embeddings
- **RotatE**: Rotation in complex space

**Score Function:**
$$f_r(h, t) = \text{score of triple } (h, r, t)$$

Higher score $\rightarrow$ more likely to be true.

#### B. Text-based Methods

Using textual descriptions with neural networks:
- **KG-BERT**: BERT for triple classification
- **BLP**: BERT + LP (link prediction)

#### C. Embedding Similarity (This Thesis)

Using semantic embeddings to find similar concepts:

```python
def find_similar_pairs(nodes, threshold=0.8):
    """
    1. Embed each node's name + description
    2. Compute cosine similarity between all pairs
    3. Filter pairs above threshold
    """
    embeddings = embed_model(nodes)  # [N, D]
    similarity = cosine_similarity(embeddings)  # [N, N]
    return pairs where similarity > threshold
```

### 4.3 Relationship Classification

After finding similar pairs, classify into typed relationships:

| Relationship | Definition | Example |
|--------------|------------|---------|
| **isPrerequisiteOf** | A must be learned before B | Hukum Newton → Gaya Gesek |
| **supports** | A helps understand B | Grafik → Vektor |
| **analogousTo** | A and B share similar patterns | Listrik → Magnet |

---

## 5. Knowledge Graph Metrics

### 5.1 Taxonomy of KG Metrics

```
KG Metrics
├── Structural Metrics
│   ├── Size Metrics (nodes, edges, density)
│   ├── Connectivity Metrics (components, diameter)
│   └── Topology Metrics (degree distribution, clustering)
│
├── Quality Metrics
│   ├── Completeness (coverage, missing values)
│   ├── Accuracy (correctness, consistency)
│   └── Timeliness (freshness, updates)
│
├── Semantic Metrics
│   ├── Coherence (logical consistency)
│   ├── Relevance (domain appropriateness)
│   └── Trustworthiness (source reliability)
│
└── Task-Specific Metrics
    ├── Extraction Quality
    ├── Completion Performance
    └── Application Metrics
```

### 5.2 Structural Metrics

#### A. Basic Statistics

| Metric | Formula | Description |
|--------|---------|-------------|
| **Node Count** | $|E|$ | Number of entities |
| **Edge Count** | $|T|$ | Number of triples |
| **Density** | $\frac{|T|}{|E|(|E|-1)}$ | Edge-to-node ratio |
| **Average Degree** | $\frac{2|T|}{|E|}$ | Connectivity measure |

#### B. Connectivity Metrics

| Metric | Formula | Description |
|--------|---------|-------------|
| **Connected Components** | CC | Number of isolated subgraphs |
| **Diameter** | $\max_{u,v} d(u,v)$ | Longest shortest path |
| **Average Path Length** | $\frac{1}{N(N-1)}\sum_{u \neq v} d(u,v)$ | Typical distance |

#### C. Centrality Metrics

**Degree Centrality:**
$$C_D(v) = \frac{deg(v)}{|E| - 1}$$

**Betweenness Centrality:**
$$C_B(v) = \sum_{s \neq v \neq t} \frac{\sigma_{st}(v)}{\sigma_{st}}$$

Where $\sigma_{st}$ = number of shortest paths from $s$ to $t$, and $\sigma_{st}(v)$ = number passing through $v$.

#### D. Community Structure

**Modularity** measures how well the graph separates into communities:

$$Q = \frac{1}{2m}\sum_{ij}\left[A_{ij} - \frac{k_i k_j}{2m}\right]\delta(c_i, c_j)$$

Where:
- $A_{ij}$ = adjacency matrix
- $k_i$ = degree of node $i$
- $m$ = total edges
- $\delta(c_i, c_j) = 1$ if nodes $i,j$ in same community

### 5.3 Extraction Quality Metrics

#### A. Completeness Metrics

| Metric | Formula | Target |
|--------|---------|--------|
| **Description Completeness** | $\frac{|\{e : desc(e) \neq \emptyset\}|}{|E|}$ | $\geq 0.95$ |
| **Property Coverage** | $\frac{|\{p : \exists(e,p,v)\}|}{|P_{schema}|}$ | $\geq 0.80$ |
| **Bloom Level Coverage** | $\frac{|\{l : \exists e, bloom(e)=l\}|}{6}$ | $= 1.0$ |

#### B. Granularity Metrics

| Metric | Formula | Interpretation |
|--------|---------|----------------|
| **Avg SubKonsep per Konsep** | $\frac{|SK|}{|K|}$ | Decomposition depth |
| **Empty SubKonsep Rate** | $\frac{|\{k : |SK(k)| = 0\}|}{|K|}$ | Should be low |
| **Hierarchy Depth** | $\max_{path} length$ | Curriculum structure |

#### C. Distribution Metrics

**Bloom's Taxonomy Distribution:**

```
Level        Expected %   Actual %
─────────────────────────────────
remember        10%          12%
understand      25%          28%
apply           30%          25%
analyze         20%          18%
evaluate        10%          12%
create           5%           5%
```

**Pyramid Compliance Score:**
$$S_{pyramid} = 1 - \frac{1}{5}\sum_{i=1}^{5}\max(0, n_{i+1} - n_i)$$

Where $n_1 < n_2 < ... < n_6$ is the expected pyramid ordering.

### 5.4 Relationship Quality Metrics

#### A. Classification Coverage

| Metric | Formula | Description |
|--------|---------|-------------|
| **Typed Relation Ratio** | $\frac{|T_{typed}|}{|T_{SIMILAR}|}$ | Classification coverage |
| **Relation Type Entropy** | $-\sum_r p_r \log p_r$ | Diversity of types |

#### B. Semantic Validity

**Prerequisite Chain Analysis:**
- Maximum chain length
- Average chain length
- Cycles detected (should be 0)

**Cross-Domain Connectivity:**
$$CD = \frac{|\{(h,t) : domain(h) \neq domain(t)\}|}{|T|}$$

### 5.5 Composite Quality Score

For thesis evaluation, combine metrics into a single score:

$$Q_{composite} = \sum_{i} w_i \cdot S_i$$

Where:
- $S_1$ = Extraction score (description completeness + Bloom coverage)
- $S_2$ = Structure score (low orphan rate + good connectivity)
- $S_3$ = Relationship score (typed ratio + cross-domain)
- $S_4$ = Curriculum alignment score (pyramid compliance + glossary hit)

**Recommended weights:**
- $w_1 = 0.30$ (Extraction)
- $w_2 = 0.25$ (Structure)
- $w_3 = 0.25$ (Relationships)
- $w_4 = 0.20$ (Curriculum)

---

## 6. Human Evaluation Methods

### 6.1 Rationale for Human Evaluation

Automated metrics cannot capture:
- **Semantic correctness** of extracted concepts
- **Pedagogical validity** of relationships
- **Domain expert agreement** with KG content

Human evaluation provides **ground truth** for:
- Validating LLM extraction quality
- Assessing relationship accuracy
- Measuring practical usefulness

### 6.2 Expert Evaluation Framework

#### A. Evaluator Selection

| Criterion | Specification |
|-----------|---------------|
| **Domain expertise** | Subject matter teachers (Fisika, Kimia, Biologi) |
| **Experience level** | Minimum 3 years teaching |
| **Familiarity** | Kurikulum Merdeka implementation |
| **Sample size** | 3 teachers (1 per subject) |

#### B. Evaluation Protocol

```
┌─────────────────────────────────────────────────────────────┐
│                    EVALUATION WORKFLOW                      │
├─────────────────────────────────────────────────────────────┤
│  1. Training (5 min)                                        │
│     └── Explain KG concept, Likert scale                    │
│                                                             │
│  2. Profile Collection (2 min)                              │
│     └── Subject, experience, grade levels                   │
│                                                             │
│  3. Concept Validation (8 min)                              │
│     └── Rate 10-15 sampled concepts                         │
│                                                             │
│  4. Relationship Validation (5 min)                         │
│     └── Rate 8-10 sampled relationships                     │
│                                                             │
│  5. Overall Assessment (3 min)                              │
│     └── Quality, usefulness, feedback                       │
│                                                             │
│  Total: ~20-25 minutes                                      │
└─────────────────────────────────────────────────────────────┘
```

### 6.3 Survey Instrument Design

#### A. Concept Validation Questions

For each sampled concept, present:
- Concept name (Konsep name)
- Description (Deskripsi)
- Bloom level assignment (Tingkat Kognitif)

**Rating Questions (5-point Likert scale):**

| Question | Scale |
|----------|-------|
| Q1: Kecocokan nama konsep | 1 (Sangat Tidak Tepat) → 5 (Sangat Tepat) |
| Q2: Kelengkapan deskripsi | 1 (Sangat Tidak Lengkap) → 5 (Sangat Lengkap) |
| Q3: Kesesuaian tingkat Bloom | 1 (Sangat Tidak Sesuai) → 5 (Sangat Sesuai) |

**Open-ended:**
- Q4: Saran koreksi (opsional)

#### B. Relationship Validation Questions

For each sampled relationship, present:
- Source concept → [Relation Type] → Target concept

**Rating Questions:**

| Question | Scale |
|----------|-------|
| Q1: Validitas relasi | 1 (Sangat Tidak Valid) → 5 (Sangat Valid) |
| Q2: Kesesuaian dengan pengalaman mengajar | 1 (Tidak Sesuai) → 5 (Sangat Sesuai) |

**Alternative selection:**
- Q3: Tipe relasi yang lebih tepat (jika tidak setuju)

#### C. Overall Assessment Questions

| Question | Type |
|----------|------|
| Kualitas keseluruhan KG | Likert 1-5 |
| Kesesuaian dengan Kurikulum Merdeka | Likert 1-5 |
| Kegunaan untuk analisis kurikulum | Likert 1-5 |
| Kelebihan sistem | Open text |
| Kekurangan sistem | Open text |
| Bersedia menggunakan di kelas? | Yes/No |

### 6.4 Aggregated Human Metrics

#### A. Per-Item Metrics

**Concept Validity Rate:**
$$VR_{concept} = \frac{|\{rating \geq 4\}|}{|\{all ratings\}|}$$

**Average Concept Accuracy:**
$$\bar{A}_{concept} = \frac{1}{N}\sum_{i=1}^{N} rating_i$$

#### B. Agreement Metrics

**Inter-Rater Agreement (Cohen's Kappa):**
$$\kappa = \frac{p_o - p_e}{1 - p_e}$$

Where:
- $p_o$ = observed agreement
- $p_e$ = expected agreement by chance

**Interpretation:**
| $\kappa$ | Agreement Level |
|----------|-----------------|
| < 0.20 | Poor |
| 0.21 - 0.40 | Fair |
| 0.41 - 0.60 | Moderate |
| 0.61 - 0.80 | Good |
| > 0.80 | Excellent |

#### C. Summary Statistics

```python
@dataclass
class SurveyAggregatedMetrics:
    # Response statistics
    total_teachers: int
    completion_rate: float

    # Concept validation
    avg_concept_accuracy: float      # Mean of 1-5 ratings
    avg_description_completeness: float
    avg_bloom_correctness: float
    concept_valid_rate: float        # % rated 4-5

    # Relationship validation
    avg_relationship_validity: float
    avg_pedagogical_agreement: float
    relationship_valid_rate: float

    # Overall assessment
    avg_overall_quality: float
    avg_curriculum_alignment: float
    would_use_rate: float
    would_recommend_rate: float
```

### 6.5 Statistical Analysis

#### A. Descriptive Statistics
- Mean, median, standard deviation for all ratings
- Frequency distributions for categorical responses

#### B. Confidence Intervals

95% confidence interval for mean rating:
$$CI = \bar{x} \pm 1.96 \cdot \frac{s}{\sqrt{n}}$$

#### C. Agreement Analysis
- Cohen's Kappa for concept validity
- Fleiss' Kappa for multiple raters (if >2)

---

## 7. Application to Curriculum Analysis

### 7.1 Domain-Specific Considerations

#### A. Indonesian Curriculum Structure (Kurikulum Merdeka)

```
Mata Pelajaran (Subject)
    │
    ├── Fase E (Kelas X)
    │   └── Document (Textbook)
    │       └── Bab (Chapter)
    │           └── SubBab (Section)
    │               └── Konsep (Concept)
    │                   └── SubKonsep (Sub-concept)
    │
    └── Fase F (Kelas XI-XII)
        └── ...
```

#### B. Bloom's Taxonomy Integration

| Level | Cognitive Process | Curriculum Example |
|-------|-------------------|-------------------|
| **Remember** | Recall facts | Menghafal rumus |
| **Understand** | Explain ideas | Menjelaskan konsep |
| **Apply** | Use information | Menyelesaikan soal |
| **Analyze** | Draw connections | Membandingkan teori |
| **Evaluate** | Justify decisions | Menilai validitas |
| **Create** | Produce new work | Merancang eksperimen |

### 7.2 Thesis Evaluation Framework

#### Research Questions

| RQ | Focus | Metrics |
|----|-------|---------|
| RQ1 | Extraction quality | Description completeness, Bloom coverage |
| RQ2 | Graph structure | Orphan rate, connectivity |
| RQ3 | Relationship discovery | Typed ratio, prerequisite chains |
| RQ4 | Human validation | Concept accuracy, relationship validity |
| RQ5 | Pedagogical usefulness | Teacher ratings, would-use rate |

#### Expected Results Table

**Table 1: Automated Metrics**
| Metric | Value | Target |
|--------|-------|--------|
| Konsep count | ~150 | - |
| SubKonsep count | ~400 | - |
| Description completeness | 95%+ | ≥ 90% |
| Bloom coverage | 6/6 levels | 6/6 |
| Typed relation ratio | 0.75 | ≥ 0.70 |
| Composite quality score | 0.80 | ≥ 0.75 |

**Table 2: Human Validation Results**
| Metric | Mean | Std Dev | 95% CI |
|--------|------|---------|--------|
| Concept accuracy | 4.2 | 0.7 | [3.8, 4.6] |
| Relationship validity | 3.9 | 0.9 | [3.4, 4.4] |
| Bloom correctness | 4.0 | 0.8 | [3.6, 4.4] |
| Overall quality | 4.1 | 0.6 | [3.7, 4.5] |

### 7.3 Limitations and Future Work

#### Limitations
1. **Scale**: Limited to 3 subjects (Fisika, Kimia, Biologi)
2. **Validators**: Only 3 teachers (1 per subject)
3. **Language**: Indonesian-specific prompts and evaluation
4. **Ground truth**: No gold standard curriculum KG for comparison

#### Future Improvements
1. Expand to more subjects and grade levels
2. Larger validator pool for statistical significance
3. Longitudinal validation with actual classroom use
4. Comparison with manually curated curriculum databases

---

## References

1. Paulheim, H. (2017). Knowledge Graph Refinement: A Survey of Approaches and Evaluation Methods. *Semantic Web*, 8(3), 489-508.

2. Ji, S., Pan, S., Cambria, E., Marttinen, P., & Yu, P. S. (2021). A Survey on Knowledge Graphs: Representation, Acquisition, and Applications. *IEEE Transactions on Neural Networks and Learning Systems*, 33(2), 494-514.

3. Bordes, A., Usunier, N., Garcia-Durán, A., Weston, J., & Yakhnenko, O. (2013). Translating Embeddings for Modeling Multi-relational Data. *NeurIPS*.

4. Wang, Q., Mao, Z., Wang, B., & Guo, L. (2017). Knowledge Graph Embedding: A Survey of Approaches and Applications. *IEEE TKDE*, 29(12), 2724-2743.

5. Färber, M., Ell, B., Menne, C., & Rettinger, A. (2015). A Comparative Survey of DBpedia, Freebase, Wikidata, and YAGO. *Semantic Web*, 1-15.

6. Anderson, L. W., & Krathwohl, D. R. (2001). *A Taxonomy for Learning, Teaching, and Assessing: A Revision of Bloom's Taxonomy*. Longman.

7. Cohen, J. (1960). A Coefficient of Agreement for Nominal Scales. *Educational and Psychological Measurement*, 20(1), 37-46.

8. Kementerian Pendidikan, Kebudayaan, Riset, dan Teknologi. (2022). *Kurikulum Merdeka*. Jakarta: Kemendikbudristek.
