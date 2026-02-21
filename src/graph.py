"""Step D: Neo4j graph construction and querying."""

from neo4j import GraphDatabase
from src.config import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD


def get_driver():
    if not NEO4J_URI or not NEO4J_PASSWORD:
        raise ValueError("NEO4J_URI and NEO4J_PASSWORD must be set")
    uri: str = NEO4J_URI
    user: str = NEO4J_USERNAME or "neo4j"
    pwd: str = NEO4J_PASSWORD
    return GraphDatabase.driver(uri, auth=(user, pwd))


def insert_topics(driver, data: dict, document_name: str = "Unknown"):
    """Insert topics into Neo4j following best practices for multi-document KGs.

    Creates a (:Document)-[:CONTAINS]->(:Topic)-[:INCLUDES]->(:SubTopic) structure.
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
