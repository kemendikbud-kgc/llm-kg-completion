"""
Ingest extraction-v3-toc-gap-byCC into a Neo4j database.

Usage:
    python experiments/scripts/ingest_v3_to_neo4j.py

Uses NEO4J_URI / NEO4J_USERNAME / NEO4J_PASSWORD from .env.
Target DB should be cleared first: MATCH (n) DETACH DELETE n
"""

import json
from pathlib import Path
from dotenv import load_dotenv
import os
from neo4j import GraphDatabase

load_dotenv()

URI = os.getenv("NEO4J_URI", "neo4j+s://5bdd4856.databases.neo4j.io")
USER = os.getenv("NEO4J_USERNAME")
PASS = os.getenv("NEO4J_PASSWORD")

BASE = Path(__file__).resolve().parent.parent / "knowledge_graph_states" / "extraction-v3-toc-gap-byCC"

FILES = [
    "Biologi Kelas XII.json",
    "Fisika Kelas XII.json",
    "Kimia Kelas XII.json",
]


def ingest(tx, grade_name, data):
    # 1. Grade
    tx.run("MERGE (g:Grade {name: $name}) SET g.type = 'Kelas XII'",
           name=grade_name)

    for i, ch in enumerate(data["chapters"]):
        ch_name = ch["chapter"]
        ch_summary = ch.get("chapter_summary", "")

        # 2. Chapter
        tx.run("""
            MATCH (g:Grade {name: $grade})
            MERGE (ch:Chapter {name: $name, grade: $grade})
            SET ch.summary = $summary, ch.order = $order
            MERGE (g)-[:HAS_CHAPTER]->(ch)
        """, grade=grade_name, name=ch_name, summary=ch_summary, order=i)

        # 3. Chapter relations (NEXT_CHAPTER, PRASYARAT, MEMPERSIAPKAN)
        if ch.get("next"):
            tx.run("""
                MATCH (ch1:Chapter {name: $from_ch, grade: $grade})
                MERGE (ch2:Chapter {name: $to_ch, grade: $grade})
                MERGE (ch1)-[:NEXT_CHAPTER]->(ch2)
            """, from_ch=ch_name, to_ch=ch["next"], grade=grade_name)

        for cr in ch.get("chapter_relations", []):
            rel_type = cr.get("type", "PRASYARAT")
            tx.run(f"""
                MATCH (ch:Chapter {{name: $from_ch, grade: $grade}})
                MERGE (ch2:Chapter {{name: $to_ch, grade: $grade}})
                MERGE (ch)-[:`{rel_type}` {{description: $desc}}]->(ch2)
            """, from_ch=ch_name, to_ch=cr.get("target_chapter", ""),
               desc=cr.get("explanation", ""), grade=grade_name)

        for st in ch["subtopics"]:
            st_name = st["name"]

            # 4. Subtopic
            tx.run("""
                MATCH (ch:Chapter {name: $chapter, grade: $grade})
                MERGE (st:Subtopic {name: $name, chapter: $chapter, grade: $grade})
                SET st.provenance = $prov
                MERGE (ch)-[:HAS_SUBTOPIC]->(st)
            """, chapter=ch_name, name=st_name, grade=grade_name,
               prov=st.get("provenance", ""))

            for c in st["concepts"]:
                c_name = c["name"]

                # 5. Concept
                tx.run("""
                    MATCH (st:Subtopic {name: $subtopic, chapter: $chapter, grade: $grade})
                    MERGE (c:Concept {name: $name, grade: $grade})
                    SET c.description = $desc,
                        c.glossary_validated = $gv,
                        c.materi_pokok_ref = $mp,
                        c.provenance = $prov
                    MERGE (st)-[:HAS_CONCEPT]->(c)
                """, subtopic=st_name, chapter=ch_name, grade=grade_name,
                   name=c_name, desc=c.get("description", ""),
                   gv=c.get("glossary_validated", False),
                   mp=c.get("materi_pokok_ref", ""),
                   prov=c.get("provenance", "extraction"))

                # 6. Relations
                for rel in c.get("relations", []):
                    rel_type = rel["type"].upper().replace(" ", "_").replace("-", "_")
                    target = rel["target"]
                    desc = rel.get("description", "")
                    prov = rel.get("provenance", "")

                    er = rel.get("expert_review", {})
                    er_status = er.get("status", "")
                    er_consensus = er.get("consensus", "")
                    er_n = er.get("n_reviewers", 0)
                    er_json = json.dumps(er, ensure_ascii=False) if er else ""

                    # Try to link to existing Concept first, fall back to ConceptTarget
                    result = tx.run(
                        "MATCH (c:Concept {name: $target, grade: $grade}) RETURN c LIMIT 1",
                        target=target, grade=grade_name
                    )
                    if result.single():
                        tx.run(f"""
                            MATCH (src:Concept {{name: $src, grade: $grade}})
                            MATCH (tgt:Concept {{name: $target, grade: $grade}})
                            MERGE (src)-[r:`{rel_type}`]->(tgt)
                            SET r.description = $desc,
                                r.original_relation_type = $orig_type,
                                r.provenance = $prov,
                                r.expert_status = $er_status,
                                r.expert_consensus = $er_consensus,
                                r.expert_n_reviewers = $er_n,
                                r.expert_review_json = $er_json
                        """, src=c_name, target=target, grade=grade_name,
                           desc=desc, orig_type=rel["type"], prov=prov,
                           er_status=er_status, er_consensus=er_consensus,
                           er_n=er_n, er_json=er_json)
                    else:
                        tx.run(f"""
                            MATCH (src:Concept {{name: $src, grade: $grade}})
                            MERGE (tgt:ConceptTarget {{name: $target, grade: $grade}})
                            MERGE (src)-[r:`{rel_type}`]->(tgt)
                            SET r.description = $desc,
                                r.original_relation_type = $orig_type,
                                r.provenance = $prov,
                                r.expert_status = $er_status,
                                r.expert_consensus = $er_consensus,
                                r.expert_n_reviewers = $er_n,
                                r.expert_review_json = $er_json
                        """, src=c_name, target=target, grade=grade_name,
                           desc=desc, orig_type=rel["type"], prov=prov,
                           er_status=er_status, er_consensus=er_consensus,
                           er_n=er_n, er_json=er_json)


def main():
    driver = GraphDatabase.driver(URI, auth=(USER, PASS))
    driver.verify_connectivity()
    print(f"Connected to {URI}")

    for filename in FILES:
        grade_name = filename.replace(".json", "")
        path = BASE / filename
        data = json.loads(path.read_text(encoding="utf-8"))

        n_concepts = sum(len(st["concepts"]) for ch in data["chapters"] for st in ch["subtopics"])
        n_rels = sum(len(r) for ch in data["chapters"] for st in ch["subtopics"] for c in st["concepts"] for r in [c.get("relations", [])])
        print(f"\nIngesting {grade_name}: {n_concepts} concepts, {n_rels} relations...")

        with driver.session() as session:
            session.execute_write(lambda tx: ingest(tx, grade_name, data))

        print(f"  Done: {grade_name}")

    # Final stats
    with driver.session() as session:
        result = session.run("""
            MATCH (n)
            RETURN labels(n)[0] AS label, count(n) AS cnt
            ORDER BY cnt DESC
        """)
        print("\n=== Final node counts ===")
        for record in result:
            print(f"  {record['label']}: {record['cnt']}")

        result = session.run("MATCH ()-[r]->() RETURN count(r) AS total_rels")
        print(f"  Total relationships: {result.single()['total_rels']}")

    driver.close()
    print("\nIngestion complete!")


if __name__ == "__main__":
    main()
