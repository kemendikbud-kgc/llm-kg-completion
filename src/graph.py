"""Step D: Neo4j graph construction and querying."""

import logging

import networkx as nx
from neo4j import GraphDatabase

from src.config import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD

logger = logging.getLogger(__name__)


def get_driver():
    if not NEO4J_URI or not NEO4J_PASSWORD:
        raise ValueError("NEO4J_URI and NEO4J_PASSWORD must be set")
    uri: str = NEO4J_URI
    user: str = NEO4J_USERNAME or "neo4j"
    pwd: str = NEO4J_PASSWORD
    return GraphDatabase.driver(uri, auth=(user, pwd))


def seed_from_daftar_isi(
    doc_structure,  # DocumentStructure from ingestion.py — avoids circular import
    document_name: str,
    driver,
) -> int:
    """Seed KG skeleton (Document, Bab, SubBab, SubSubBab nodes) from the Daftar Isi.

    Runs *before* extraction so the structural nodes exist even if LLM
    extraction fails or is partial.  All operations use MERGE so re-running
    is idempotent.

    Returns the number of distinct Bab + SubBab + SubSubBab nodes merged.
    """
    if not doc_structure.found or not doc_structure.entries:
        return 0

    count = 0
    with driver.session() as session:
        session.run(
            "MERGE (d:Document {name: $doc_name}) ON CREATE SET d.uploaded_at = timestamp()",
            doc_name=document_name,
        )

        seen_babs: set[str] = set()
        seen_sub_babs: set[tuple[str, str]] = set()  # (bab, sub_bab)
        seen_sub_sub_babs: set[tuple[str, str, str]] = (
            set()
        )  # (bab, sub_bab, sub_sub_bab)

        for entry in doc_structure.entries:
            bab_name = entry.bab

            if bab_name not in seen_babs:
                seen_babs.add(bab_name)
                session.run(
                    """
                    MERGE (b:Bab {name: $bab_name, document: $doc_name})
                    WITH b
                    MATCH (d:Document {name: $doc_name})
                    MERGE (d)-[:hasBab]->(b)
                    """,
                    bab_name=bab_name,
                    doc_name=document_name,
                )
                count += 1

            if entry.sub_bab:
                sub_bab_key = (bab_name, entry.sub_bab)
                if sub_bab_key not in seen_sub_babs:
                    seen_sub_babs.add(sub_bab_key)
                    session.run(
                        """
                        MERGE (sb:SubBab {name: $sub_bab_name, bab: $bab_name, document: $doc_name})
                        WITH sb
                        MATCH (b:Bab {name: $bab_name, document: $doc_name})
                        MERGE (b)-[:hasSubBab]->(sb)
                        """,
                        sub_bab_name=entry.sub_bab,
                        bab_name=bab_name,
                        doc_name=document_name,
                    )
                    count += 1

            if entry.sub_sub_bab and entry.sub_bab:
                sub_sub_bab_key = (bab_name, entry.sub_bab, entry.sub_sub_bab)
                if sub_sub_bab_key not in seen_sub_sub_babs:
                    seen_sub_sub_babs.add(sub_sub_bab_key)
                    session.run(
                        """
                        MERGE (ssb:SubSubBab {name: $sub_sub_bab_name, sub_bab: $sub_bab_name, bab: $bab_name, document: $doc_name})
                        WITH ssb
                        MATCH (sb:SubBab {name: $sub_bab_name, bab: $bab_name, document: $doc_name})
                        MERGE (sb)-[:hasSubSubBab]->(ssb)
                        """,
                        sub_sub_bab_name=entry.sub_sub_bab,
                        sub_bab_name=entry.sub_bab,
                        bab_name=bab_name,
                        doc_name=document_name,
                    )
                    count += 1

    return count


def insert_konsep(
    driver,
    data: dict,
    document_name: str = "Unknown",
    kelas: str | None = None,
    subject_name: str | None = None,
    subject_phase: str | None = None,
):
    """Insert konsep into Neo4j following the new KG ontology.

    Creates:
      (:MataPelajaran)-[:hasDocument]->(:Document {kelas})-[:hasBab]->(:Bab)
        -[:hasSubBab]->(:SubBab)-[:hasSubSubBab]->(:SubSubBab)-[:hasKonsep]->(:Konsep)
        -[:hasSubKonsep]->(:SubKonsep)

    When sub_bab is None, Konsep is linked directly to Bab (no SubBab node).
    When sub_sub_bab is None, Konsep is linked to SubBab (no SubSubBab node).
    Konsep are shared across documents (MERGE on name) to enable cross-doc linking.
    """
    with driver.session() as session:
        # Create the Document node
        session.run(
            """
            MERGE (d:Document {name: $doc_name})
            SET d.uploaded_at = timestamp(), d.kelas = $kelas
            """,
            doc_name=document_name,
            kelas=kelas or "",
        )

        # Create MataPelajaran node and link to Document if provided
        if subject_name:
            session.run(
                """
                MERGE (mp:MataPelajaran {name: $subject_name})
                SET mp.phase = $phase
                WITH mp
                MATCH (d:Document {name: $doc_name})
                MERGE (mp)-[:hasDocument]->(d)
                """,
                subject_name=subject_name,
                phase=subject_phase or "",
                doc_name=document_name,
            )

        # Group konsep by (bab, sub_bab, sub_sub_bab)
        # Skip concepts without bab assignment (ToC is source of truth)
        # Skip concepts with non-ToC bab names (e.g., LLM-detected "Meiosis")
        bab_map: dict[str, dict[str | None, dict[str | None, list[dict]]]] = {}
        skipped_no_bab = 0
        skipped_invalid_bab = 0
        for konsep in data.get("konsep", []):
            bab_name = konsep.get("bab")
            if not bab_name:
                logger.warning(
                    "Konsep '%s' has no bab assignment, skipping",
                    konsep.get("name", "<unnamed>"),
                )
                skipped_no_bab += 1
                continue
            # Validate bab_name follows ToC format (starts with "Bab " or "BAB ")
            if not (bab_name.startswith("Bab ") or bab_name.startswith("BAB ")):
                logger.warning(
                    "Konsep '%s' has non-ToC bab name '%s', skipping",
                    konsep.get("name", "<unnamed>"), bab_name
                )
                skipped_invalid_bab += 1
                continue
            sub_bab_name: str | None = konsep.get("sub_bab") or None
            sub_sub_bab_name: str | None = konsep.get("sub_sub_bab") or None
            bab_map.setdefault(bab_name, {}).setdefault(sub_bab_name, {}).setdefault(
                sub_sub_bab_name, []
            ).append(konsep)

        if skipped_no_bab > 0:
            logger.info(
                "Skipped %d konsep without bab assignment (ToC is source of truth)",
                skipped_no_bab,
            )
        if skipped_invalid_bab > 0:
            logger.info(
                "Skipped %d konsep with non-ToC bab names (LLM-detected names rejected)",
                skipped_invalid_bab,
            )

        for bab_name, sub_bab_dict in bab_map.items():
            # Only link to existing Bab nodes (created by seed_from_daftar_isi)
            # Do NOT create new Bab nodes here - ToC is the single source of truth
            result = session.run(
                """
                MATCH (b:Bab {name: $bab_name, document: $doc_name})
                RETURN b.name as found
                """,
                bab_name=bab_name,
                doc_name=document_name,
            )
            record = result.single()
            if not record:
                konsep_count = sum(
                    len(kl) for sb_dict in sub_bab_dict.values()
                    for kl in sb_dict.values()
                )
                logger.warning(
                    "Bab '%s' not found in graph (not in ToC?), skipping %d konsep",
                    bab_name, konsep_count
                )
                continue

            for sub_bab_name, sub_sub_bab_dict in sub_bab_dict.items():
                if sub_bab_name:
                    # Create SubBab node linked to Bab
                    session.run(
                        """
                        MERGE (sb:SubBab {name: $sub_bab_name, bab: $bab_name, document: $doc_name})
                        WITH sb
                        MATCH (b:Bab {name: $bab_name, document: $doc_name})
                        MERGE (b)-[:hasSubBab]->(sb)
                        """,
                        sub_bab_name=sub_bab_name,
                        bab_name=bab_name,
                        doc_name=document_name,
                    )

                for sub_sub_bab_name, konsep_list in sub_sub_bab_dict.items():
                    if sub_bab_name and sub_sub_bab_name:
                        # Create SubSubBab node linked to SubBab
                        session.run(
                            """
                            MERGE (ssb:SubSubBab {name: $sub_sub_bab_name, sub_bab: $sub_bab_name, bab: $bab_name, document: $doc_name})
                            WITH ssb
                            MATCH (sb:SubBab {name: $sub_bab_name, bab: $bab_name, document: $doc_name})
                            MERGE (sb)-[:hasSubSubBab]->(ssb)
                            """,
                            sub_sub_bab_name=sub_sub_bab_name,
                            sub_bab_name=sub_bab_name,
                            bab_name=bab_name,
                            doc_name=document_name,
                        )

                    for konsep in konsep_list:
                        # MERGE Konsep (shared across documents)
                        session.run(
                            """
                            MERGE (k:Konsep {name: $name})
                            SET k.description = $desc, k.bloom_level = $bloom
                            """,
                            name=konsep["name"],
                            desc=konsep.get("description", ""),
                            bloom=konsep.get("bloom_level"),
                        )

                        # Link to the most specific structural node available
                        if sub_bab_name and sub_sub_bab_name:
                            # Link SubSubBab -> Konsep
                            session.run(
                                """
                                MATCH (ssb:SubSubBab {name: $sub_sub_bab_name, sub_bab: $sub_bab_name, bab: $bab_name, document: $doc_name})
                                MATCH (k:Konsep {name: $konsep_name})
                                MERGE (ssb)-[:hasKonsep]->(k)
                                """,
                                sub_sub_bab_name=sub_sub_bab_name,
                                sub_bab_name=sub_bab_name,
                                bab_name=bab_name,
                                doc_name=document_name,
                                konsep_name=konsep["name"],
                            )
                        elif sub_bab_name:
                            # Link SubBab -> Konsep
                            session.run(
                                """
                                MATCH (sb:SubBab {name: $sub_bab_name, bab: $bab_name, document: $doc_name})
                                MATCH (k:Konsep {name: $konsep_name})
                                MERGE (sb)-[:hasKonsep]->(k)
                                """,
                                sub_bab_name=sub_bab_name,
                                bab_name=bab_name,
                                doc_name=document_name,
                                konsep_name=konsep["name"],
                            )
                        else:
                            # Fallback: link Bab -> Konsep directly (no SubBab)
                            session.run(
                                """
                                MATCH (b:Bab {name: $bab_name, document: $doc_name})
                                MATCH (k:Konsep {name: $konsep_name})
                                MERGE (b)-[:hasKonsep]->(k)
                                """,
                                bab_name=bab_name,
                                doc_name=document_name,
                                konsep_name=konsep["name"],
                            )

                        # Handle sub-konsep
                        for sub in konsep.get("sub_konsep", []):
                            session.run(
                                """
                                MERGE (sk:SubKonsep {name: $name})
                                SET sk.description = $desc, sk.bloom_level = $bloom
                                WITH sk
                                MATCH (k:Konsep {name: $konsep_name})
                                MERGE (k)-[:hasSubKonsep]->(sk)
                                """,
                                name=sub["name"],
                                desc=sub.get("description", ""),
                                bloom=sub.get("bloom_level"),
                                konsep_name=konsep["name"],
                            )


# Backward-compat wrapper
def insert_topics(
    driver,
    data: dict,
    document_name: str = "Unknown",
    subject_name: str | None = None,
    subject_phase: str | None = None,
):
    """Legacy wrapper for insert_konsep. Converts old format if needed."""
    # Handle old format {"topics": [...]} -> {"konsep": [...]}
    if "topics" in data and "konsep" not in data:
        konsep = []
        for t in data.get("topics", []):
            sub_konsep = [
                {
                    "name": s["name"],
                    "description": s.get("description", ""),
                    "bloom_level": None,
                }
                for s in t.get("sub_topics", [])
            ]
            konsep.append(
                {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "bloom_level": None,
                    "bab": None,
                    "sub_konsep": sub_konsep,
                }
            )
        data = {"konsep": konsep}

    insert_konsep(
        driver,
        data,
        document_name=document_name,
        subject_name=subject_name,
        subject_phase=subject_phase,
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
            OPTIONAL MATCH (d)-[:hasBab]->(:Bab)-[:hasKonsep]->(k:Konsep)
            RETURN d.name AS name, d.kelas AS kelas, d.uploaded_at AS uploaded_at,
                   count(DISTINCT k) AS topic_count
            ORDER BY d.uploaded_at DESC
            """
        )
        return [dict(r) for r in result]


def get_document_topics(driver, document_name: str) -> list:
    """Get all konsep for a specific document."""
    with driver.session() as session:
        result = session.run(
            """
            MATCH (d:Document {name: $doc_name})-[:hasBab]->(b:Bab)-[:hasKonsep]->(k:Konsep)
            OPTIONAL MATCH (k)-[:hasSubKonsep]->(sk:SubKonsep)
            RETURN k.name AS topic, k.description AS topic_desc,
                   k.bloom_level AS bloom_level, b.name AS bab,
                   collect({name: sk.name, description: sk.description}) AS subtopics
            """,
            doc_name=document_name,
        )
        return [dict(r) for r in result]


def get_graph_stats(driver) -> dict:
    """Get statistics about the knowledge graph."""
    with driver.session() as session:
        result = session.run(
            """
            OPTIONAL MATCH (mp:MataPelajaran) WITH count(mp) AS subjects
            OPTIONAL MATCH (d:Document) WITH subjects, count(d) AS documents
            OPTIONAL MATCH (b:Bab) WITH subjects, documents, count(b) AS babs
            OPTIONAL MATCH (sb:SubBab) WITH subjects, documents, babs, count(sb) AS sub_babs
            OPTIONAL MATCH (k:Konsep) WITH subjects, documents, babs, sub_babs, count(k) AS konsep
            OPTIONAL MATCH (sk:SubKonsep) WITH subjects, documents, babs, sub_babs, konsep, count(sk) AS sub_konsep
            OPTIONAL MATCH ()-[r:SIMILAR_TO]->() WITH subjects, documents, babs, sub_babs, konsep, sub_konsep, count(r) AS similar_rels
            OPTIONAL MATCH ()-[r2:isPrerequisiteOf]->() WITH subjects, documents, babs, sub_babs, konsep, sub_konsep, similar_rels, count(r2) AS prereq_rels
            OPTIONAL MATCH ()-[r3:supports]->() WITH subjects, documents, babs, sub_babs, konsep, sub_konsep, similar_rels, prereq_rels, count(r3) AS supports_rels
            OPTIONAL MATCH ()-[r4:analogousTo]->()
            RETURN subjects, documents, babs, sub_babs, konsep, sub_konsep, similar_rels,
                   prereq_rels, supports_rels, count(r4) AS analogous_rels
            """
        )
        row = result.single()
        if row:
            return {
                "subjects": row["subjects"],
                "documents": row["documents"],
                "babs": row["babs"],
                "sub_babs": row["sub_babs"],
                "topics": row["konsep"],  # keep "topics" key for backward compat
                "subtopics": row[
                    "sub_konsep"
                ],  # keep "subtopics" key for backward compat
                "konsep": row["konsep"],
                "sub_konsep": row["sub_konsep"],
                "similar_rels": row["similar_rels"],
                "prereq_rels": row["prereq_rels"],
                "supports_rels": row["supports_rels"],
                "analogous_rels": row["analogous_rels"],
            }
        return {
            "subjects": 0,
            "documents": 0,
            "babs": 0,
            "sub_babs": 0,
            "topics": 0,
            "subtopics": 0,
            "konsep": 0,
            "sub_konsep": 0,
            "similar_rels": 0,
            "prereq_rels": 0,
            "supports_rels": 0,
            "analogous_rels": 0,
        }


def get_all_topics_with_subtopics(driver) -> list:
    """Get all konsep with their sub-konsep across all documents."""
    with driver.session() as session:
        result = session.run(
            """
            MATCH (k:Konsep)
            OPTIONAL MATCH (k)-[:hasSubKonsep]->(sk:SubKonsep)
            OPTIONAL MATCH (b:Bab)-[:hasKonsep]->(k)
            OPTIONAL MATCH (d:Document)-[:hasBab]->(b)
            RETURN k.name AS name, k.description AS description,
                   k.bloom_level AS bloom_level,
                   collect(DISTINCT {name: sk.name, description: sk.description}) AS subtopics,
                   collect(DISTINCT d.name) AS documents
            ORDER BY k.name
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


def get_typed_relationships(driver) -> list:
    """Get all typed concept relationships (isPrerequisiteOf, supports, analogousTo)."""
    with driver.session() as session:
        result = session.run(
            """
            MATCH (a)-[r]->(b)
            WHERE type(r) IN ['isPrerequisiteOf', 'supports', 'analogousTo']
            RETURN a.name AS source, b.name AS target,
                   type(r) AS rel_type, r.confidence AS confidence
            ORDER BY rel_type, source
            """
        )
        return [dict(r) for r in result]


def create_typed_relationship(
    driver,
    source: str,
    target: str,
    rel_type: str,
    confidence: float | None = None,
) -> None:
    """Create a typed relationship between two Konsep nodes."""
    valid_types = {"isPrerequisiteOf", "supports", "analogousTo"}
    if rel_type not in valid_types:
        raise ValueError(f"rel_type must be one of {valid_types}")

    with driver.session() as session:
        session.run(
            f"""
            MATCH (a:Konsep {{name: $src}})
            MATCH (b:Konsep {{name: $tgt}})
            MERGE (a)-[r:{rel_type}]->(b)
            SET r.confidence = $confidence
            """,
            src=source,
            tgt=target,
            confidence=confidence,
        )


def get_nodes_with_descriptions(
    driver,
    document_name: str | None = None,
    include_cross_doc: bool = False,
) -> list[dict]:
    """Get Konsep nodes with their names and descriptions for embedding.

    Args:
        driver: Neo4j driver
        document_name: If provided, filter to this document only
        include_cross_doc: If True with document_name, also include nodes from
                          other documents

    Returns list of dicts with 'name', 'description', 'labels', and 'document'.
    Falls back to name as description if description is empty.
    """
    with driver.session() as session:
        if document_name and not include_cross_doc:
            result = session.run(
                """
                MATCH (d:Document {name: $doc_name})-[:hasBab]->(b:Bab)-[:hasKonsep]->(k:Konsep)
                RETURN k.name AS name, k.description AS description,
                       labels(k) AS labels, d.name AS doc_name
                UNION
                MATCH (d:Document {name: $doc_name})-[:hasBab]->(:Bab)-[:hasKonsep]->(:Konsep)
                      -[:hasSubKonsep]->(sk:SubKonsep)
                RETURN sk.name AS name, sk.description AS description,
                       labels(sk) AS labels, d.name AS doc_name
                ORDER BY name
                """,
                doc_name=document_name,
            )
        elif document_name and include_cross_doc:
            result = session.run(
                """
                MATCH (n)
                WHERE n:Konsep OR n:SubKonsep
                RETURN n.name AS name, n.description AS description,
                       labels(n) AS labels, NULL AS doc_name
                ORDER BY name
                """,
                doc_name=document_name,
            )
        else:
            result = session.run(
                """
                MATCH (n)
                WHERE n:Konsep OR n:SubKonsep
                OPTIONAL MATCH (d:Document)-[:hasBab]->(:Bab)-[:hasKonsep]->(n)
                OPTIONAL MATCH (d2:Document)-[:hasBab]->(:Bab)-[:hasKonsep]->(:Konsep)
                       -[:hasSubKonsep]->(n)
                WITH n, COALESCE(d.name, d2.name) AS doc_name
                RETURN n.name AS name, n.description AS description,
                       labels(n) AS labels, doc_name
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
    """Calculate graph quality metrics: ADC and Modularity.

    Uses Konsep and SubKonsep nodes and their relationships.
    """
    G = nx.Graph()

    with driver.session() as session:
        nodes = session.run(
            """
            MATCH (n) WHERE n:Konsep OR n:SubKonsep
            RETURN elementId(n) AS id, n.name AS name
            """
        )
        for r in nodes:
            G.add_node(r["id"])

        edges = session.run(
            """
            MATCH (a)-[r]->(b)
            WHERE (a:Konsep OR a:SubKonsep) AND (b:Konsep OR b:SubKonsep)
            RETURN elementId(a) AS src, elementId(b) AS tgt
            """
        )
        for r in edges:
            G.add_edge(r["src"], r["tgt"])

    if G.number_of_nodes() == 0:
        return {"adc": 0.0, "modularity": 0.0, "density": 0.0, "components": 0}

    centrality = nx.degree_centrality(G)
    adc = sum(centrality.values()) / len(centrality)

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
