"""Step D: Neo4j graph construction and querying."""

import networkx as nx
from neo4j import GraphDatabase

from src.config import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD


def get_driver():
    if not NEO4J_URI or not NEO4J_PASSWORD:
        raise ValueError("NEO4J_URI and NEO4J_PASSWORD must be set")
    uri: str = NEO4J_URI
    user: str = NEO4J_USERNAME or "neo4j"
    pwd: str = NEO4J_PASSWORD
    return GraphDatabase.driver(uri, auth=(user, pwd))


def insert_topics(
    driver,
    data: dict,
    document_name: str = "Unknown",
    subject_name: str | None = None,
    subject_phase: str | None = None,
):
    """Insert topics into Neo4j following best practices for multi-document KGs.

    Creates a (:Subject)-[:CONTAINS]->(:Document)-[:CONTAINS]->(:Topic)-[:INCLUDES]->(:SubTopic) structure.
    Topics are shared across documents (MERGE on name), enabling cross-document linking.
    """
    with driver.session() as session:
        # Create the Document node
        session.run(
            """
            MERGE (d:Document {name: $doc_name})
            SET d.uploaded_at = timestamp()
            """,
            doc_name=document_name,
        )

        # Create Subject node and link to Document if provided
        if subject_name:
            session.run(
                """
                MERGE (s:Subject {name: $subject_name})
                SET s.phase = $phase
                WITH s
                MATCH (d:Document {name: $doc_name})
                MERGE (s)-[:CONTAINS]->(d)
                """,
                subject_name=subject_name,
                phase=subject_phase or "",
                doc_name=document_name,
            )

        for topic in data["topics"]:
            # MERGE topic (shared across documents)
            session.run(
                "MERGE (t:Topic {name: $name}) SET t.description = $desc",
                name=topic["name"],
                desc=topic.get("description", ""),
            )

            # Link Document -> Topic
            session.run(
                """
                MATCH (d:Document {name: $doc_name})
                MATCH (t:Topic {name: $topic_name})
                MERGE (d)-[:CONTAINS]->(t)
                """,
                doc_name=document_name,
                topic_name=topic["name"],
            )

            # Handle subtopics
            for sub in topic.get("sub_topics", []):
                session.run(
                    """
                    MERGE (s:SubTopic {name: $name}) SET s.description = $desc
                    WITH s
                    MATCH (t:Topic {name: $topic_name})
                    MERGE (t)-[:INCLUDES]->(s)
                    """,
                    name=sub["name"],
                    desc=sub.get("description", ""),
                    topic_name=topic["name"],
                )


def get_all_nodes(driver) -> list:
    with driver.session() as session:
        result = session.run("MATCH (n) RETURN n.name AS name, labels(n) AS labels")
        return [dict(r) for r in result]


def get_all_documents(driver) -> list:
    """Get all documents in the knowledge graph."""
    with driver.session() as session:
        result = session.run(
            """
            MATCH (d:Document)
            OPTIONAL MATCH (d)-[:CONTAINS]->(t:Topic)
            RETURN d.name AS name, d.uploaded_at AS uploaded_at, count(t) AS topic_count
            ORDER BY d.uploaded_at DESC
            """
        )
        return [dict(r) for r in result]


def get_document_topics(driver, document_name: str) -> list:
    """Get all topics for a specific document."""
    with driver.session() as session:
        result = session.run(
            """
            MATCH (d:Document {name: $doc_name})-[:CONTAINS]->(t:Topic)
            OPTIONAL MATCH (t)-[:INCLUDES]->(s:SubTopic)
            RETURN t.name AS topic, t.description AS topic_desc,
                   collect({name: s.name, description: s.description}) AS subtopics
            """,
            doc_name=document_name,
        )
        return [dict(r) for r in result]


def get_graph_stats(driver) -> dict:
    """Get statistics about the knowledge graph."""
    with driver.session() as session:
        result = session.run(
            """
            OPTIONAL MATCH (subj:Subject) WITH count(subj) AS subjects
            OPTIONAL MATCH (d:Document) WITH subjects, count(d) AS documents
            OPTIONAL MATCH (t:Topic) WITH subjects, documents, count(t) AS topics
            OPTIONAL MATCH (s:SubTopic) WITH subjects, documents, topics, count(s) AS subtopics
            OPTIONAL MATCH ()-[r:CONTAINS]->() WITH subjects, documents, topics, subtopics, count(r) AS contains_rels
            OPTIONAL MATCH ()-[r:INCLUDES]->() WITH subjects, documents, topics, subtopics, contains_rels, count(r) AS includes_rels
            OPTIONAL MATCH ()-[r:SIMILAR_TO]->()
            RETURN subjects, documents, topics, subtopics, contains_rels, includes_rels, count(r) AS similar_rels
            """
        )
        row = result.single()
        if row:
            return {
                "subjects": row["subjects"],
                "documents": row["documents"],
                "topics": row["topics"],
                "subtopics": row["subtopics"],
                "contains_rels": row["contains_rels"],
                "includes_rels": row["includes_rels"],
                "similar_rels": row["similar_rels"],
            }
        return {
            "subjects": 0,
            "documents": 0,
            "topics": 0,
            "subtopics": 0,
            "contains_rels": 0,
            "includes_rels": 0,
            "similar_rels": 0,
        }


def get_all_topics_with_subtopics(driver) -> list:
    """Get all topics with their subtopics across all documents."""
    with driver.session() as session:
        result = session.run(
            """
            MATCH (t:Topic)
            OPTIONAL MATCH (t)-[:INCLUDES]->(s:SubTopic)
            OPTIONAL MATCH (d:Document)-[:CONTAINS]->(t)
            RETURN t.name AS name, t.description AS description,
                   collect(DISTINCT {name: s.name, description: s.description}) AS subtopics,
                   collect(DISTINCT d.name) AS documents
            ORDER BY t.name
            """
        )
        return [dict(r) for r in result]


def get_similar_relationships(driver) -> list:
    """Get all SIMILAR_TO relationships."""
    with driver.session() as session:
        result = session.run(
            """
            MATCH (a)-[r:SIMILAR_TO]->(b)
            RETURN a.name AS source, b.name AS target, r.score AS score
            ORDER BY r.score DESC
            """
        )
        return [dict(r) for r in result]


def get_nodes_with_descriptions(
    driver,
    document_name: str | None = None,
    include_cross_doc: bool = False,
) -> list[dict]:
    """Get nodes with their names and descriptions for embedding.

    Args:
        driver: Neo4j driver
        document_name: If provided, filter to this document only
        include_cross_doc: If True with document_name, also include nodes from other
                          documents that share topics with the selected document

    Returns list of dicts with 'name', 'description', 'labels', and 'document'.
    Falls back to name as description if description is empty.
    """
    with driver.session() as session:
        if document_name and not include_cross_doc:
            # Single document mode - only topics from this document
            result = session.run(
                """
                MATCH (d:Document {name: $doc_name})-[:CONTAINS]->(t:Topic)
                OPTIONAL MATCH (t)-[:INCLUDES]->(s:SubTopic)
                WITH t, s, d
                RETURN t.name AS name, t.description AS description, labels(t) AS labels, d.name AS doc_name
                UNION
                MATCH (d:Document {name: $doc_name})-[:CONTAINS]->(:Topic)-[:INCLUDES]->(s:SubTopic)
                RETURN s.name AS name, s.description AS description, labels(s) AS labels, d.name AS doc_name
                ORDER BY name
                """,
                doc_name=document_name,
            )
        elif document_name and include_cross_doc:
            # Cross-document mode - topics from selected doc + related topics from other docs
            result = session.run(
                """
                MATCH (d:Document {name: $doc_name})-[:CONTAINS]->(t:Topic)
                WITH collect(DISTINCT t) AS selected_topics
                MATCH (n)
                WHERE n:Topic OR n:SubTopic
                RETURN n.name AS name, n.description AS description, labels(n) AS labels, NULL AS doc_name
                ORDER BY name
                """,
                doc_name=document_name,
            )
        else:
            # All documents mode
            result = session.run(
                """
                MATCH (n)
                WHERE n:Topic OR n:SubTopic
                OPTIONAL MATCH (d:Document)-[:CONTAINS]->(n)
                OPTIONAL MATCH (d2:Document)-[:CONTAINS]->(:Topic)-[:INCLUDES]->(n)
                WITH n, COALESCE(d.name, d2.name) AS doc_name
                RETURN n.name AS name, n.description AS description, labels(n) AS labels, doc_name
                ORDER BY n.name
                """
            )

        nodes = []
        seen_names = set()
        for r in result:
            name = r["name"]
            if name in seen_names:
                continue
            seen_names.add(name)
            desc = r["description"] or name
            nodes.append(
                {
                    "name": name,
                    "description": desc,
                    "labels": r["labels"],
                    "document": r.get("doc_name"),
                }
            )
        return nodes


def get_graph_quality_metrics(driver) -> dict:
    """Calculate graph quality metrics: ADC (Average Degree Centrality) and Modularity.

    These metrics are used to evaluate the effectiveness of KG completion.
    ADC measures average connectivity; Modularity measures community structure.
    """
    G = nx.Graph()

    with driver.session() as session:
        # Get nodes (Topics and SubTopics only)
        nodes = session.run(
            """
            MATCH (n) WHERE n:Topic OR n:SubTopic
            RETURN elementId(n) AS id, n.name AS name
            """
        )
        for r in nodes:
            G.add_node(r["id"])

        # Get edges (INCLUDES and SIMILAR_TO relationships)
        edges = session.run(
            """
            MATCH (a)-[r]->(b)
            WHERE (a:Topic OR a:SubTopic) AND (b:Topic OR b:SubTopic)
            RETURN elementId(a) AS src, elementId(b) AS tgt
            """
        )
        for r in edges:
            G.add_edge(r["src"], r["tgt"])

    if G.number_of_nodes() == 0:
        return {"adc": 0.0, "modularity": 0.0, "density": 0.0, "components": 0}

    # Average Degree Centrality (ADC)
    centrality = nx.degree_centrality(G)
    adc = sum(centrality.values()) / len(centrality)

    # Modularity (measures community structure quality)
    try:
        communities = list(nx.community.greedy_modularity_communities(G))
        modularity = (
            nx.community.modularity(G, communities) if len(communities) > 1 else 0.0
        )
    except Exception:
        modularity = 0.0

    return {
        "adc": round(adc, 3),
        "modularity": round(modularity, 3),
        "density": round(nx.density(G), 3),
        "components": nx.number_connected_components(G),
    }
