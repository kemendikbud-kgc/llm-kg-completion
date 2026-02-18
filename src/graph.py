"""Step D: Neo4j graph construction and querying."""

from neo4j import GraphDatabase
from src.config import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD


def get_driver():
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))


def insert_topics(driver, data: dict):
    with driver.session() as session:
        for topic in data["topics"]:
            session.run(
                "MERGE (t:Topic {name: $name}) SET t.description = $desc",
                name=topic["name"],
                desc=topic.get("description", ""),
            )
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
