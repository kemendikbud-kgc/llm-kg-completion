# Paper Analysis: LLM-Assisted Knowledge Graph Completion for Curriculum and Domain Modelling

## 1. Paper Metadata

- **Title:** LLM-Assisted Knowledge Graph Completion for Curriculum and Domain Modelling in Personalized Higher Education Recommendations
- **Authors:** Hasan Abu-Rasheed, Constance Jumbo, Rashed Al Amin, Christian Weber, Veit Wiese, Roman Obermaisser, Madjid Fathi
- **Year:** 2025
- **Venue/Journal:** IEEE Global Engineering Education Conference (EDUCON2025), London, UK
- **Paper Type:** Framework proposal with empirical evaluation
- **DOI/URL:** arXiv:2501.12300v1 [cs.HC] - https://arxiv.org/abs/2501.12300

---

## 2. Comprehensive Summary

### Research Context & Motivation

The paper addresses the challenge of personalizing learning paths in higher education, where students often have diverse backgrounds (especially in international programs) but face rigid, one-size-fits-all curricula. The authors identify a critical problem: teachers lack time to analyze individual student backgrounds and cross-reference content across courses, while universities lack standardized representations of course content that would enable meaningful comparison and integration across programs and institutions.

The key gap the paper identifies is the absence of comprehensive, interoperable models that link three crucial dimensions: curriculum content (what is taught), domain knowledge (broader field context), and user models (student backgrounds and goals). Traditional approaches focus narrowly on user and educational models without adequate domain representation, limiting the potential for truly personalized learning recommendations.

The research motivation is fundamentally practical: enabling students to avoid redundant learning of topics they already know while discovering relevant content from other courses, faculties, or even institutions that could accelerate their learning toward professional goals.

### Methodology & Approach

The paper proposes a four-step implementation strategy for LLM-assisted knowledge graph completion:

1. **Ontology Definition:** A three-model ontology covering curriculum (Module → Lecture → Session → Topic → SubTopic), domain (Domain → SubDomain → DomainTopic), and user (User → Profile → Background Knowledge, Learning Goals, Preferences). The Topic/SubTopic hierarchy is central, with Topics being abstract concepts and SubTopics being the fine-grained content explained through learning materials.

2. **Automated Extraction:** A pipeline using OpenAI's Whisper for video transcription and GPT-4o for topic extraction and classification. The LLM is prompted with ontology-based context (definitions of Topic vs SubTopic classes) to ensure consistent extraction across different sources.

3. **Human-AI Collaboration:** Teachers validate LLM predictions, making final decisions on topics, sub-topics, and descriptions. Teachers also contribute to prompt engineering by providing domain-specific definitions and rules.

4. **KG Construction:** Two-phase process creating nodes from validated content then edges from both hierarchical relationships (ontology-defined) and semantic similarity (NLP-computed using title and description embeddings).

The approach was evaluated on two university modules: "Embedded Systems" and "Development of Embedded Systems Using FPGA" from the University of Siegen.

### Key Findings & Results

The extraction pipeline achieved high accuracy across both modules:
- **Embedded Systems:** Topic P=0.99, R=0.94, F1=0.96; SubTopic P=1.0, R=0.97, F1=0.98; Description P=1.0
- **FPGA Module:** Topic P=0.97, R=1.0, F1=0.98; SubTopic P=0.89, R=0.99, F1=0.94; Description P=0.89

A total of 1,197 extraction samples were evaluated (173 Topics, 512 SubTopics, 512 Descriptions). The slight quality difference between modules was traced to variations in lecture recording styles—live sessions with Q&A vs. structured explanations.

Graph structural metrics showed improvement after semantic linking: Average Degree Centrality increased from 0.9 to 1.03, and modularity decreased from 0.769 to 0.767 (lower modularity indicates stronger cross-module connections, which is desirable). While improvements were modest due to high similarity thresholds and small dataset, expert feedback was strongly positive about the practical utility for course restructuring and student personalization.

### Contributions & Novelty

1. **Three-model ontology** integrating curriculum, domain, and user models for higher education (highly relevant to KG completion)
2. **LLM-assisted extraction pipeline** for topic/subtopic extraction from lecture materials (directly applicable)
3. **Human-AI collaborative workflow** ensuring quality while reducing teacher effort (process innovation)
4. **Ontology-contextualized prompting** strategy for consistent LLM extraction (technique applicable to any domain)
5. **Dual relation extraction** combining hierarchical ontology relations with semantic similarity (relevant to completion)
6. **Semi-supervised validation** approach for scaling relation validation (practical for large KGs)
7. **RAG suggestion** for using KG as context source for improved extraction (future direction)

### Limitations & Future Work

**Acknowledged Limitations:**
- Small-scale evaluation (2 modules, 18 sessions total)
- High similarity thresholds limiting discovered relations
- Variability in lecture recording quality affecting extraction
- No automated prerequisite/temporal relationship extraction
- User model not fully implemented in evaluation

**Future Directions:**
- Scale to larger course collections across institutions
- Integrate RAG with KG as context source for extraction
- Implement personalized learning path recommendation algorithms
- Add prerequisite relationship detection
- Cross-institutional knowledge graph federation

---

## 3. Method Extraction

### Method: Three-Model Higher Education Ontology

- **Description:** A formal ontology structure that separates concerns into three interconnected models: curriculum (educational content hierarchy), domain (real-world knowledge context), and user (learner characteristics). The key insight is that connecting curriculum topics to domain concepts enables cross-course discovery, while the user model enables personalization based on background knowledge and goals.

- **How It Works:**
  1. Define curriculum hierarchy: Module → Lecture → Session → Topic → SubTopic
  2. Define domain hierarchy: Domain → SubDomain → DomainTopic
  3. Define user profile: User → (Background Knowledge, Learning Goals, Preferences, Academic Parameters)
  4. Create cross-model relations: Topic ↔ DomainTopic (equivalent_to), Session ↔ Scenario (happens_in)
  5. Enable queries like "find topics related to student's background" or "find sessions covering similar domain concepts"

- **Applicable To:** `schemas.py`, `graph.py`

- **Implementation Complexity:** Medium - requires extending current Pydantic schemas and Neo4j graph model, but no algorithmic complexity

- **Expected Benefit:** Enables cross-document relationship discovery and domain-level analysis. The paper shows this enables lecturers to identify overlapping content between courses.

- **Dependencies:** None beyond current stack

- **Risks/Tradeoffs:** More complex schema increases extraction complexity; need to define domain taxonomy

- **Paper Reference:** Section 3.1, Figure 1 (p. 3-4)

---

### Method: Ontology-Contextualized LLM Prompting

- **Description:** Rather than generic topic extraction prompts, the LLM is given explicit definitions of ontology classes (Topic = abstract concept, SubTopic = fine-grained content explained in materials) along with hierarchical constraints (each Topic contains SubTopics). This contextual grounding significantly improves extraction consistency and accuracy.

- **How It Works:**
  1. Include ontology class definitions in system prompt
  2. Specify hierarchical constraints (Topic contains SubTopics)
  3. Provide domain-specific terminology definitions (teacher input)
  4. Set explicit rules for handling edge cases (e.g., Q&A in transcripts)
  5. Request structured output matching ontology schema

- **Applicable To:** `extraction.py`

- **Implementation Complexity:** Low - primarily prompt engineering, already using Pydantic for structure

- **Expected Benefit:** Paper achieved 0.94-0.98 F1 on Topic extraction, 0.94-0.98 F1 on SubTopic extraction. Current project could see similar improvements in extraction consistency.

- **Dependencies:** None - can be applied to existing LlamaIndex extraction

- **Risks/Tradeoffs:** Domain-specific prompts may need adjustment per curriculum type; Indonesian curriculum may have different conventions than German technical courses

- **Paper Reference:** Section 3.2 (p. 4-5)

---

### Method: Description-Enhanced Semantic Similarity

- **Description:** Uses both titles AND detailed descriptions of topics/subtopics for semantic similarity computation. Descriptions are auto-generated from lecture content, providing richer semantic signal than titles alone. The paper notes descriptions are especially valuable for SubTopics since they represent the detailed explained content.

- **How It Works:**
  1. Extract descriptions alongside topics/subtopics during LLM extraction
  2. Concatenate title + description for embedding input
  3. Generate embeddings using text embedding model
  4. Compute cosine similarity between topic pairs
  5. Create SIMILAR_TO edges above threshold
  6. Validate sample of edges with human expert

- **Applicable To:** `extraction.py`, `completion.py`, `schemas.py`

- **Implementation Complexity:** Low - current project already has embedding-based similarity; needs description field addition

- **Expected Benefit:** Richer semantic representations should improve similarity quality. Paper notes descriptions are "essential" for finding meaningful cross-course connections.

- **Dependencies:** None beyond current stack

- **Risks/Tradeoffs:** Longer text → higher embedding costs; description quality affects similarity quality

- **Paper Reference:** Section 3.2, 3.4 (p. 4-6)

---

### Method: Semi-Supervised Relation Validation

- **Description:** For scalability, instead of validating all predicted similarity relations, a random sample is validated by human experts. Feedback from validation is used to adjust similarity thresholds and LLM prompts iteratively, creating a feedback loop that improves relation quality over time.

- **How It Works:**
  1. Generate all similarity relations above initial threshold
  2. Random sample N relations for expert review
  3. Expert marks relations as valid/invalid
  4. Calculate precision on sample
  5. If precision low: raise threshold or adjust embedding approach
  6. If precision high: lower threshold to increase recall
  7. Iterate until satisfactory quality-quantity tradeoff

- **Applicable To:** `completion.py`, `app.py` (validation UI)

- **Implementation Complexity:** Medium - requires building validation UI and feedback loop

- **Expected Benefit:** Enables scaling to large KGs while maintaining quality. Paper notes this is necessary "due to the large amount of semantic relations that can be identified."

- **Dependencies:** Validation UI component (could extend Streamlit app)

- **Risks/Tradeoffs:** Sample may not be representative; requires ongoing expert involvement

- **Paper Reference:** Section 3.4 (p. 6)

---

### Method: KG-as-Context RAG for Extraction

- **Description:** Once a knowledge graph is constructed, it becomes a context source for future extractions. When extracting topics from new lectures in similar domains, existing KG content is retrieved and provided as context, improving extraction relevance and consistency.

- **How It Works:**
  1. New document arrives for extraction
  2. Identify domain/subject area from metadata or initial analysis
  3. Query KG for existing topics in that domain
  4. Include relevant existing topics in LLM extraction prompt as context
  5. LLM extraction benefits from seeing existing topic structure
  6. New topics can reference or link to existing ones

- **Applicable To:** `extraction.py`, `completion.py`

- **Implementation Complexity:** Medium - requires KG query integration into extraction pipeline

- **Expected Benefit:** Paper notes this is "particularly effective when the topic extraction and classification are done to a lecture that is contextually similar to the existing content of the KG." Could improve consistency across multiple curriculum documents.

- **Dependencies:** Working KG with queryable topics; RAG retrieval mechanism

- **Risks/Tradeoffs:** May bias extraction toward existing topics; cold start problem for empty KG

- **Paper Reference:** Section 3.4, 4.1 (p. 6-7)

---

### Method: Graph Quality Metrics (ADC & Modularity)

- **Description:** Uses Average Degree Centrality (ADC) and Graph Modularity to evaluate KG quality. ADC measures node connectivity (higher = more relations discovered). Modularity measures how separable the graph is into clusters (lower = better cross-cluster connections). These metrics quantify the KG completion task success.

- **How It Works:**
  1. Calculate ADC: average of (node degree / max possible degree) across all nodes
  2. Calculate Modularity: measure of how well graph decomposes into communities
  3. Compare before/after adding semantic similarity edges
  4. ADC increase + Modularity decrease = successful KG completion

- **Applicable To:** `completion.py`, `app.py` (metrics display)

- **Implementation Complexity:** Low - standard graph algorithms, available in networkx

- **Expected Benefit:** Quantitative evaluation of KG completion quality. Paper showed ADC: 0.9 → 1.03, Modularity: 0.769 → 0.767 improvement.

- **Dependencies:** networkx or similar graph analysis library

- **Risks/Tradeoffs:** Metrics are proxies; high ADC could also indicate over-linking

- **Paper Reference:** Section 4.2 (p. 7-8)

---

### Method: Multi-Source Input Fusion

- **Description:** Combines multiple input sources (lecture slides, manuscripts, video transcripts) to improve extraction quality. Different sources provide complementary information: slides have structure, manuscripts have detail, videos have explanation context.

- **How It Works:**
  1. Extract text from slides (structured, bullet points)
  2. Extract text from manuscripts/PDFs (detailed explanations)
  3. Transcribe lecture videos using Whisper ASR
  4. Merge/concatenate sources per session
  5. Feed combined text to LLM for extraction
  6. Cross-reference extractions for validation

- **Applicable To:** `ingestion.py`, `extraction.py`

- **Implementation Complexity:** High - requires video processing, ASR integration, source alignment

- **Expected Benefit:** Paper notes diversifying input "will be important to ensure good quality extraction" especially when individual sources are noisy (e.g., live session recordings with Q&A).

- **Dependencies:** OpenAI Whisper or similar ASR; video processing libraries

- **Risks/Tradeoffs:** Significantly increases pipeline complexity; video processing is resource-intensive

- **Paper Reference:** Section 3.2, 4.1 (p. 4, 7)

---

## 4. Priority Matrix

| Method | Impact (1-5) | Effort (1-5) | Fit (1-5) | Priority Score |
|--------|-------------|--------------|-----------|----------------|
| Description-Enhanced Similarity | 4 | 2 | 5 | 10.0 |
| Ontology-Contextualized Prompting | 4 | 2 | 5 | 10.0 |
| Graph Quality Metrics | 3 | 1 | 5 | 15.0 |
| Three-Model Ontology (Domain Model) | 5 | 3 | 4 | 6.7 |
| KG-as-Context RAG | 4 | 3 | 4 | 5.3 |
| Semi-Supervised Validation | 3 | 3 | 4 | 4.0 |
| Multi-Source Input Fusion | 3 | 5 | 3 | 1.8 |

**Priority Rankings:**
1. **Graph Quality Metrics** - Trivial to implement, provides valuable evaluation capability
2. **Description-Enhanced Similarity** - Low effort, high impact, perfect fit with current architecture
3. **Ontology-Contextualized Prompting** - Can improve extraction immediately via prompt updates
4. **Three-Model Ontology** - Transformative for project goals but requires schema extension
5. **KG-as-Context RAG** - Natural evolution once KG is populated
6. **Semi-Supervised Validation** - Valuable for scaling but requires UI work
7. **Multi-Source Input Fusion** - High effort, current PDF-only approach may suffice

---

## 5. Gap Analysis

### What the paper does that we don't:

| Capability | Paper's Approach | Why It Matters |
|------------|------------------|----------------|
| **Domain Model** | Explicit Domain → SubDomain → DomainTopic hierarchy linked to curriculum | Enables reasoning about knowledge areas beyond individual courses |
| **User Model** | Background Knowledge, Learning Goals, Preferences as graph entities | Foundation for personalized recommendations |
| **Video Transcription** | Whisper ASR for lecture videos | Richer content source for extraction |
| **Human Validation Loop** | Teachers validate and refine LLM outputs | Ensures quality, builds teacher trust |
| **Cross-Module Linking** | Semantic similarity across different courses | Discovers hidden curriculum overlaps |
| **Prompt Contextualization** | Ontology definitions in prompts | Improves extraction consistency |
| **Graph Quality Metrics** | ADC, Modularity measurements | Quantifies KG completion success |

### What we do that the paper doesn't cover:

| Our Capability | Description |
|----------------|-------------|
| **Caching** | SHA-256 based disk cache for extraction results |
| **Multi-Provider LLM** | litellm abstraction supporting Gemini, OpenAI, Anthropic |
| **Local Embeddings** | HuggingFace models as alternative to API embeddings |
| **Streamlit Visualization** | Interactive graph exploration UI |
| **Pydantic Validation** | Structured output enforcement via LlamaIndex |

### Key Architectural Differences:

**Graph Schema:**
- Paper: Module → Lecture → Session → Topic → SubTopic + Domain model + User model
- Ours: Document → Topic → SubTopic (simpler, no domain/user models)

**Entity Types:**
- Paper: 12+ node types across three models
- Ours: 2 node types (Topic, SubTopic)

**Relationship Types:**
- Paper: has_a, includes, equivalent_to, happens_in, semantic similarity
- Ours: INCLUDES, SIMILAR_TO (fewer semantic relationships)

**Embedding Approach:**
- Paper: Title + Description concatenation for similarity
- Ours: Description only (could benefit from enrichment)

**Completion Method:**
- Paper: Semantic similarity + LLM-assisted relation finding
- Ours: Cosine similarity threshold only

### Opportunities for Synthesis:

1. **Extend schema progressively:** Add Domain model first (SubjectArea concept), then User model later
2. **Enrich extraction:** Add description generation to current TopicExtraction schema
3. **Improve prompts:** Incorporate ontology definitions into extraction prompts
4. **Add metrics:** Implement ADC/Modularity for evaluation
5. **Build toward RAG:** Store embeddings in way that enables retrieval for future extractions

---

## 6. Implementation Roadmap

### 6.1 Description-Enhanced Semantic Similarity

**Files to modify:**
- `src/schemas.py` - Add description field to SubTopic if not present
- `src/extraction.py` - Ensure descriptions are extracted for all entities
- `src/completion.py` - Use title+description for embedding

**Implementation approach:**
```python
# schemas.py - Ensure SubTopic has description
class SubTopic(BaseModel):
    name: str
    description: str  # Add if missing or ensure populated

# completion.py - Enhanced embedding text
def get_embedding_text(node: dict) -> str:
    """Combine title and description for richer embedding."""
    name = node.get('name', '')
    description = node.get('description', '')
    # Concatenate with separator for clarity
    return f"{name}: {description}" if description else name

# Update embed_nodes to use enhanced text
def embed_nodes(nodes: list[dict], embed_model) -> list[tuple[dict, list[float]]]:
    texts = [get_embedding_text(node) for node in nodes]
    embeddings = embed_model.get_text_embedding_batch(texts)
    return list(zip(nodes, embeddings))
```

**Integration points:**
- Modify `completion.py:find_similar_pairs()` to use enhanced text
- Ensure extraction prompts request descriptions for all entities

**Testing strategy:**
- Compare similarity quality before/after on sample documents
- Check that descriptions are being populated during extraction
- Verify embedding dimensions unchanged

**Potential challenges:**
- Empty descriptions for some entities
- Longer text may affect embedding quality for some models
- Need to handle None/empty description gracefully

---

### 6.2 Ontology-Contextualized Prompting

**Files to modify:**
- `src/extraction.py` - Update extraction prompts with ontology context

**Implementation approach:**
```python
# extraction.py - Enhanced system prompt
ONTOLOGY_CONTEXT = """
You are extracting educational content from curriculum documents.

ONTOLOGY DEFINITIONS:
- Topic: An abstract concept or theme being taught in the educational material.
  Topics represent the "what" of learning at a conceptual level.
- SubTopic: Fine-grained content that explains or elaborates a Topic.
  SubTopics represent specific knowledge items covered in detail.

HIERARCHICAL CONSTRAINT:
- Each Topic MUST contain one or more SubTopics
- SubTopics are ALWAYS nested under a parent Topic
- Topics are mutually exclusive (a concept belongs to one Topic)

EXTRACTION RULES:
1. Extract Topics as abstract, overarching concepts
2. Extract SubTopics as specific, detailed content items
3. Generate descriptions that capture what is taught, not general knowledge
4. Focus on curriculum content, ignore administrative/procedural text
"""

def create_extraction_prompt(text: str, context: str = "") -> str:
    return f"""{ONTOLOGY_CONTEXT}

{f"CONTEXT FROM EXISTING KNOWLEDGE GRAPH:{chr(10)}{context}" if context else ""}

Extract all Topics and SubTopics from the following educational content:

{text}
"""
```

**Integration points:**
- Integrate into existing `LLMTextCompletionProgram` prompts
- Could add domain-specific rules as configuration

**Testing strategy:**
- Compare extraction quality on same documents with old vs new prompts
- Check Topic/SubTopic ratio consistency across documents
- Verify hierarchical constraints are respected

**Potential challenges:**
- Indonesian curriculum may have different conventions
- Prompt length limits with very long context
- Need domain expert input for terminology definitions

---

### 6.3 Graph Quality Metrics

**Files to modify:**
- `src/completion.py` - Add metric calculation functions
- `app.py` - Display metrics in UI

**Implementation approach:**
```python
# completion.py - Add graph quality metrics
import networkx as nx
from neo4j import GraphDatabase

def calculate_graph_metrics(driver) -> dict:
    """Calculate ADC and Modularity for the knowledge graph."""

    # Build networkx graph from Neo4j
    G = nx.Graph()

    with driver.session() as session:
        # Get all nodes
        nodes = session.run("MATCH (n) RETURN id(n) as id, labels(n) as labels")
        for record in nodes:
            G.add_node(record['id'], labels=record['labels'])

        # Get all relationships
        rels = session.run("MATCH (a)-[r]->(b) RETURN id(a) as source, id(b) as target, type(r) as type")
        for record in rels:
            G.add_edge(record['source'], record['target'], type=record['type'])

    metrics = {}

    # Average Degree Centrality
    if G.number_of_nodes() > 0:
        degree_centrality = nx.degree_centrality(G)
        metrics['average_degree_centrality'] = sum(degree_centrality.values()) / len(degree_centrality)
    else:
        metrics['average_degree_centrality'] = 0

    # Graph Modularity (using Louvain communities)
    try:
        from community import community_louvain
        partition = community_louvain.best_partition(G)
        metrics['modularity'] = community_louvain.modularity(partition, G)
    except ImportError:
        # Fallback: use networkx greedy modularity
        communities = nx.community.greedy_modularity_communities(G)
        metrics['modularity'] = nx.community.modularity(G, communities)

    # Additional useful metrics
    metrics['node_count'] = G.number_of_nodes()
    metrics['edge_count'] = G.number_of_edges()
    metrics['density'] = nx.density(G)

    return metrics

def compare_metrics_before_after(driver, similarity_threshold: float) -> dict:
    """Compare metrics before and after adding similarity edges."""
    before = calculate_graph_metrics(driver)

    # Add similarity edges (existing completion logic)
    add_similarity_edges(driver, threshold=similarity_threshold)

    after = calculate_graph_metrics(driver)

    return {
        'before': before,
        'after': after,
        'delta': {
            'adc_change': after['average_degree_centrality'] - before['average_degree_centrality'],
            'modularity_change': after['modularity'] - before['modularity'],
            'edges_added': after['edge_count'] - before['edge_count']
        }
    }
```

**Integration points:**
- Call from `app.py` after KG completion step
- Display in Streamlit sidebar or dedicated metrics tab

**Testing strategy:**
- Verify metrics match manual calculations on small test graph
- Test with empty graph, single node, disconnected components
- Compare to paper's reported values on similar-sized graphs

**Potential challenges:**
- Modularity calculation requires undirected graph
- Large graphs may be slow to analyze
- Need to install python-louvain or use networkx alternative

---

## 7. Action Items

Prioritized checklist of next steps:

1. [ ] **Add graph quality metrics** - Implement ADC and Modularity calculations in `completion.py`, display in Streamlit app. (Effort: 2hrs)

2. [ ] **Enhance extraction prompts with ontology context** - Update `extraction.py` with explicit Topic/SubTopic definitions and hierarchical constraints. (Effort: 1hr)

3. [ ] **Ensure descriptions are extracted for all entities** - Verify `schemas.py` includes description fields, update extraction to populate them. (Effort: 1hr)

4. [ ] **Use title+description for similarity embeddings** - Modify `completion.py` to concatenate fields for richer semantic representation. (Effort: 30min)

5. [ ] **Add Domain entity type to schema** - Extend `schemas.py` with Subject/Domain class, update `graph.py` to create Domain nodes and relations. (Effort: 3hrs)

6. [ ] **Implement validation sampling UI** - Add Streamlit component to review random sample of SIMILAR_TO edges with accept/reject buttons. (Effort: 4hrs)

7. [ ] **Investigate RAG for extraction context** - Prototype querying existing KG topics as context for new document extraction. (Effort: 4hrs)

8. [ ] **Document Indonesian curriculum conventions** - Create domain-specific terminology definitions for prompt engineering based on actual curriculum analysis. (Effort: 2hrs)

---

## Summary

This paper is **highly relevant** to the current project - it addresses the exact same problem (LLM-assisted KG completion for curriculum analysis) with a similar technical approach (LLM extraction → graph storage → semantic similarity). The key differentiator is their three-model ontology (curriculum + domain + user) which enables richer cross-course discovery.

**Quick wins** (items 1-4) can be implemented in a few hours and should noticeably improve extraction quality and provide evaluation metrics.

**Medium-term enhancements** (items 5-7) would significantly expand the project's capabilities toward the paper's vision of cross-document and cross-domain relationship discovery.

The paper validates the overall approach being taken in this project while providing a clear roadmap for enhancements.
