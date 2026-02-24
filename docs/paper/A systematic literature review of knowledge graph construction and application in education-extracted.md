# Improvement Methods from Literature Review

Based on: *Abu-Salih & Alotaibi (2024). A systematic literature review of knowledge graph construction and application in education. Heliyon 10, e25383.*

## Overview

This document outlines potential improvements to the LLM-KG Completion project based on methods identified in the systematic literature review of 120 papers on educational knowledge graphs.

---

## 1. Richer Relationship Types

**Current state:** Only `INCLUDES` and `SIMILAR_TO` relationships.

**Improvement (from Fig. 3 of the paper):**

Add semantic relationship types commonly used in educational KGs:

```
(:Topic)-[:hasKeyObjective]->(:LearningObjective)
(:Topic)-[:hasPrerequisite]->(:Topic)
(:Topic)-[:hasCriticalSkill]->(:Skill)
(:SubTopic)-[:isA]->(:LearningObjective)
(:Topic)-[:hasFundamentalPrinciples]->(:Concept)
```

**Implementation:** Extend `schemas.py`:

```python
class SubTopic(BaseModel):
    name: str
    description: str
    learning_objectives: list[str] = []
    prerequisites: list[str] = []  # References to other topics
    skills: list[str] = []
```

**References:** Fig. 3, Refs [63], [67]

---

## 2. External Knowledge Linking

**Method:** Link extracted concepts to Wikipedia/DBpedia for enrichment and prerequisite discovery.

**Implementation:**

```python
# In completion.py - add DBpedia/Wikidata linking
from SPARQLWrapper import SPARQLWrapper, JSON

def link_to_dbpedia(concept_name: str) -> dict:
    """Find matching DBpedia entity for concept enrichment."""
    sparql = SPARQLWrapper("http://dbpedia.org/sparql")
    query = f"""
    SELECT ?resource ?abstract WHERE {{
        ?resource rdfs:label "{concept_name}"@en .
        ?resource dbo:abstract ?abstract .
        FILTER (lang(?abstract) = 'en')
    }} LIMIT 1
    """
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    return sparql.query().convert()
```

**Benefits:**
- Validate extracted concepts against authoritative sources
- Enrich descriptions with additional context
- Discover relationships not present in source PDF

**References:** Refs [16], [109]

---

## 3. Prerequisite Relationship Discovery

**Method:** Use embedding similarity + heuristics to infer prerequisite relationships.

**Implementation:**

```python
def discover_prerequisites(graph, embed_model, threshold=0.7):
    """
    Infer prerequisite relationships based on:
    1. Embedding similarity
    2. Topic ordering in curriculum (earlier topics → prerequisites)
    3. Concept complexity (simpler → complex)
    """
    topics = graph.get_all_topics_ordered()  # By appearance in PDF

    for i, topic_a in enumerate(topics):
        for topic_b in topics[i+1:]:  # Only forward relationships
            similarity = cosine_similarity(
                embed_model.get_embedding(topic_a.description),
                embed_model.get_embedding(topic_b.description)
            )
            if similarity > threshold:
                # topic_a likely prerequisite of topic_b
                graph.create_relationship(
                    topic_a, "PREREQUISITE_OF", topic_b,
                    properties={"confidence": similarity}
                )
```

**References:** Ref [109]

---

## 4. Multi-Hop Reasoning for Gap Detection

**Method:** Use graph path analysis to find missing connections between topics that are indirectly related.

**Implementation:**

```python
# In completion.py - add path-based completion
def find_missing_links_via_paths(graph, max_hops=3):
    """
    Find topic pairs connected by paths but missing direct links.
    Based on BGNN-TT approach from Ref [17].
    """
    query = """
    MATCH path = (a:Topic)-[*2..3]-(b:Topic)
    WHERE a <> b
    AND NOT (a)-[:SIMILAR_TO]-(b)
    AND NOT (a)-[:PREREQUISITE_OF]-(b)
    WITH a, b, count(path) as path_count,
         min(length(path)) as shortest_path
    WHERE path_count >= 2
    RETURN a.name, b.name, path_count, shortest_path
    ORDER BY path_count DESC
    """
    return graph.run_query(query)
```

**References:** Refs [17], [113]

---

## 5. Hybrid Schema Approach

**Method:** Define an ontology schema before extraction, then validate extracted data against it.

**Implementation:**

```python
# New file: src/ontology.py
EDUCATION_ONTOLOGY = {
    "entity_types": [
        "Topic", "SubTopic", "LearningObjective",
        "Skill", "Competency", "Assessment"
    ],
    "relation_types": [
        ("Topic", "INCLUDES", "SubTopic"),
        ("Topic", "PREREQUISITE_OF", "Topic"),
        ("Topic", "DEVELOPS", "Skill"),
        ("SubTopic", "ACHIEVES", "LearningObjective"),
        ("LearningObjective", "ASSESSED_BY", "Assessment"),
    ],
    "constraints": {
        "Topic": {"required": ["name", "description"]},
        "LearningObjective": {"required": ["name", "bloom_level"]},
    }
}

def validate_extraction(extraction: TopicExtraction) -> list[str]:
    """Validate extracted data against ontology schema."""
    errors = []
    for topic in extraction.topics:
        for field in EDUCATION_ONTOLOGY["constraints"]["Topic"]["required"]:
            if not getattr(topic, field, None):
                errors.append(f"Topic missing required field: {field}")
    return errors
```

**References:** Refs [63], [67]

---

## 6. Confidence Scoring for Relationships

**Method:** Add multi-factor confidence scores to all relationships for better filtering and explainability.

**Implementation:**

```python
from pydantic import BaseModel

class RelationshipScore(BaseModel):
    embedding_similarity: float  # Current approach
    co_occurrence: float         # How often terms appear together in text
    structural: float            # Graph structure (common neighbors)

    @property
    def combined_score(self) -> float:
        return (
            0.4 * self.embedding_similarity +
            0.3 * self.co_occurrence +
            0.3 * self.structural
        )

def calculate_co_occurrence(text: str, term_a: str, term_b: str, window=50) -> float:
    """Calculate co-occurrence score based on proximity in text."""
    # Find positions of both terms
    # Score based on average distance when both appear
    pass

def calculate_structural_score(graph, node_a, node_b) -> float:
    """Calculate structural similarity (common neighbors, Jaccard index)."""
    query = """
    MATCH (a)-[]-(common)-[]-(b)
    WHERE a.name = $name_a AND b.name = $name_b
    WITH a, b, count(DISTINCT common) as common_neighbors
    MATCH (a)-[]-(na)
    WITH a, b, common_neighbors, count(DISTINCT na) as a_neighbors
    MATCH (b)-[]-(nb)
    RETURN common_neighbors, a_neighbors, count(DISTINCT nb) as b_neighbors
    """
    # Jaccard index: common / (a + b - common)
    pass
```

**References:** Ref [36]

---

## 7. LLM-Based Link Prediction and Validation

**Method:** Use LLM to validate proposed relationships and suggest new ones.

**Implementation:**

```python
def llm_validate_relationship(llm, topic_a: str, topic_b: str) -> dict:
    """Use LLM to validate and classify relationship between topics."""
    prompt = f"""
    Given two curriculum topics from Indonesian education:

    Topic A: {topic_a}
    Topic B: {topic_b}

    Determine:
    1. Is there a meaningful educational relationship? (yes/no)
    2. Relationship type: prerequisite, similar, part_of, builds_upon, or none
    3. Direction: A→B, B→A, or bidirectional
    4. Confidence (0.0-1.0)
    5. Brief justification (1 sentence)

    Output as JSON:
    {{"has_relationship": bool, "type": str, "direction": str, "confidence": float, "justification": str}}
    """
    return llm.complete(prompt, output_cls=RelationshipValidation)

def llm_suggest_missing_relationships(llm, topic: str, all_topics: list[str]) -> list[dict]:
    """Use LLM to suggest relationships that might be missing."""
    prompt = f"""
    Given the topic: {topic}

    And the following other topics in the curriculum:
    {', '.join(all_topics[:20])}  # Limit for context window

    Suggest up to 3 topics that should have a relationship with "{topic}" but might be missing.
    For each, specify the relationship type and direction.

    Output as JSON array.
    """
    return llm.complete(prompt)
```

**References:** Refs [137]-[141] (Future directions section)

---

## 8. Bloom's Taxonomy Classification

**Method:** Classify learning objectives by Bloom's taxonomy level for richer semantic representation.

**Implementation:**

```python
BLOOM_LEVELS = [
    "Remember",    # recall facts and basic concepts
    "Understand",  # explain ideas or concepts
    "Apply",       # use information in new situations
    "Analyze",     # draw connections among ideas
    "Evaluate",    # justify a decision or course of action
    "Create"       # produce new or original work
]

BLOOM_KEYWORDS = {
    "Remember": ["define", "list", "recall", "identify", "name"],
    "Understand": ["explain", "describe", "interpret", "summarize"],
    "Apply": ["use", "implement", "solve", "demonstrate"],
    "Analyze": ["compare", "contrast", "examine", "differentiate"],
    "Evaluate": ["judge", "critique", "justify", "assess"],
    "Create": ["design", "construct", "develop", "formulate"]
}

def classify_bloom_level(objective: str) -> str:
    """Classify a learning objective by Bloom's taxonomy."""
    objective_lower = objective.lower()
    for level, keywords in BLOOM_KEYWORDS.items():
        if any(kw in objective_lower for kw in keywords):
            return level
    return "Unknown"
```

**References:** Common in educational KG literature, supports curriculum alignment analysis

---

## Priority Matrix

| Priority | Method | Effort | Impact | Status |
|----------|--------|--------|--------|--------|
| 1 | Richer relationship types | Low | High | Not started |
| 2 | Confidence scoring | Low | Medium | Not started |
| 3 | Prerequisite discovery | Medium | High | Not started |
| 4 | LLM-based link validation | Medium | High | Not started |
| 5 | Bloom's taxonomy classification | Low | Medium | Not started |
| 6 | External knowledge linking | High | Medium | Not started |
| 7 | Multi-hop reasoning | Medium | Medium | Not started |
| 8 | Hybrid schema approach | Medium | Medium | Not started |

---

## Key Gaps Addressed

These improvements address the following limitations identified in the literature review:

1. **Limited relationship types** → Methods 1, 3
2. **Poor evaluation techniques** → Method 6 (confidence scoring)
3. **Lack of standardization** → Method 5 (ontology schema)
4. **Sparse data** → Methods 2, 4 (external linking, LLM suggestions)
5. **No prerequisite modeling** → Method 3
6. **Limited LLM integration** → Methods 4, 7

---

## Next Steps

1. Start with low-effort, high-impact improvements (Methods 1, 2, 6)
2. Implement prerequisite discovery to add significant value
3. Add LLM validation as a quality assurance layer
4. Consider external knowledge linking for Indonesian curriculum specifics
