"""Curated Cypher query library for stakeholder presentation and Neo4j Bloom."""

QUERIES: list[dict] = [
    {
        "title": "Cross-Subject Analogies",
        "description": "Konsep pairs that are analogous across different mata pelajaran — the anti-silo finding of this thesis.",
        "category": "🎯 Thesis Core",
        "bloom_phrase": "Show cross-subject analogies",
        "cypher": """\
MATCH (mp1:MataPelajaran)-[:hasDocument]->()-[:hasBab]->()-[:hasKonsep]->(k1:Konsep)
MATCH (mp2:MataPelajaran)-[:hasDocument]->()-[:hasBab]->()-[:hasKonsep]->(k2:Konsep)
MATCH (k1)-[:analogousTo]-(k2)
WHERE mp1.name < mp2.name
RETURN mp1.name AS subject_a, k1.name AS konsep_a,
       k2.name AS konsep_b, mp2.name AS subject_b
ORDER BY subject_a, subject_b""",
    },
    {
        "title": "Prerequisite Chains",
        "description": "Full prerequisite dependency paths starting from a named Konsep (up to 4 hops).",
        "category": "🎯 Thesis Core",
        "bloom_phrase": "Show prerequisite chains from concept",
        "cypher": """\
MATCH path = (k:Konsep {name: $name})-[:isPrerequisiteOf*1..4]->(downstream:Konsep)
RETURN path""",
    },
    {
        "title": "Supports Relationships",
        "description": "Functional dependencies: Konsep A supports understanding of Konsep B.",
        "category": "🎯 Thesis Core",
        "bloom_phrase": "Show supports relationships",
        "cypher": """\
MATCH (a:Konsep)-[r:supports]->(b:Konsep)
RETURN a.name AS source_konsep, b.name AS target_konsep,
       r.confidence AS confidence
ORDER BY confidence DESC""",
    },
    {
        "title": "Curriculum Overview",
        "description": "Full structural hierarchy: MataPelajaran → Document → Bab.",
        "category": "📚 Structure",
        "bloom_phrase": "Show curriculum structure",
        "cypher": """\
MATCH (mp:MataPelajaran)-[:hasDocument]->(d:Document)-[:hasBab]->(b:Bab)
RETURN mp.name AS mata_pelajaran, mp.phase AS phase,
       d.name AS document, d.kelas AS kelas,
       b.name AS bab
ORDER BY mp.name, d.name, b.name""",
    },
    {
        "title": "Konsep by Subject",
        "description": "All Konsep grouped under each MataPelajaran.",
        "category": "📚 Structure",
        "bloom_phrase": "Show all concepts by subject",
        "cypher": """\
MATCH (mp:MataPelajaran)-[:hasDocument]->()-[:hasBab]->()-[:hasKonsep]->(k:Konsep)
RETURN mp.name AS mata_pelajaran, k.name AS konsep, k.description AS description
ORDER BY mp.name, k.name""",
    },
    {
        "title": "Most Connected Konsep",
        "description": "Top 10 Konsep by number of typed relationships (isPrerequisiteOf, supports, analogousTo).",
        "category": "📊 Analytics",
        "bloom_phrase": "Show most connected concepts",
        "cypher": """\
MATCH (k:Konsep)
OPTIONAL MATCH (k)-[r:isPrerequisiteOf|supports|analogousTo]-()
RETURN k.name AS konsep, count(r) AS connections
ORDER BY connections DESC
LIMIT 10""",
    },
    {
        "title": "Cross-Subject Supports",
        "description": "Supports relationships that span different mata pelajaran.",
        "category": "📊 Analytics",
        "bloom_phrase": "Show cross-subject supports",
        "cypher": """\
MATCH (mp1:MataPelajaran)-[:hasDocument]->()-[:hasBab]->()-[:hasKonsep]->(k1:Konsep)
MATCH (mp2:MataPelajaran)-[:hasDocument]->()-[:hasBab]->()-[:hasKonsep]->(k2:Konsep)
MATCH (k1)-[r:supports]->(k2)
WHERE mp1.name <> mp2.name
RETURN mp1.name AS subject_source, k1.name AS source_konsep,
       k2.name AS target_konsep, mp2.name AS subject_target,
       r.confidence AS confidence
ORDER BY confidence DESC""",
    },
    {
        "title": "Full Graph Overview",
        "description": "All Konsep nodes and all typed relationships — the complete picture of discovered connections.",
        "category": "🗺️ Exploration",
        "bloom_phrase": "Show full knowledge graph",
        "cypher": """\
MATCH (k1:Konsep)-[r:isPrerequisiteOf|supports|analogousTo]->(k2:Konsep)
RETURN k1, r, k2""",
    },
    {
        "title": "Konsep Neighborhood",
        "description": "All relationships of a single named Konsep in any direction (parameterised by $name).",
        "category": "🗺️ Exploration",
        "bloom_phrase": "Show concept neighborhood",
        "cypher": """\
MATCH (k:Konsep {name: $name})-[r:isPrerequisiteOf|supports|analogousTo]-(neighbor:Konsep)
RETURN k, r, neighbor""",
    },
]
