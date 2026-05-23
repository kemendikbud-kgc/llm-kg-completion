"""Ingest extraction-v2-reviewed JSONs into a Neo4j Aura instance.

DESTRUCTIVE: wipes the target DB before writing.

Reads:
  - experiments/knowledge_graph_states/extraction-v2-reviewed/{Biologi,Fisika,Kimia} Kelas XII.json

Writes (Yhoga schema, regardless of target DB):
  - 3 Grade
  - 17 Chapter (+ summary)
  - ~77 Subtopic + the "Expert Proposed Triples" synthetic subtopic(s)
  - ~570 Concept + a handful of ConceptTarget stubs
  - Structural edges: HAS_CHAPTER, HAS_SUBTOPIC, HAS_CONCEPT
  - Chapter-level: NEXT_CHAPTER, PRASYARAT, MEMPERSIAPKAN, BERKAITAN_DENGAN (from chapter_relations)
  - Concept-level typed edges with expert_review_* properties preserved

Relation type names are normalized to UPPER_SNAKE_CASE for Cypher
compatibility; the original verbatim type is preserved on each edge as
`original_relation_type`. The full `expert_review` block is preserved as
both flat scalar properties (status / consensus / n_reviewers) and a
JSON-string property (`expert_review_json`) for full audit.

USAGE:
    # Default target = yhoga (NEO4J_URI_YHOGA) — preserves legacy behavior
    python experiments/scripts/ingest_extraction_v2_reviewed.py

    # Target the default project Neo4j (NEO4J_URI) — needs src.connection
    python experiments/scripts/ingest_extraction_v2_reviewed.py --target default

    # Preview only — no writes
    python experiments/scripts/ingest_extraction_v2_reviewed.py --target default --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

REPO = Path(__file__).resolve().parent.parent.parent
SRC_DIR = REPO / "experiments" / "knowledge_graph_states" / "extraction-v2-reviewed"

GRADE_FILES = ("Biologi Kelas XII.json", "Fisika Kelas XII.json", "Kimia Kelas XII.json")


def normalize_rel_type(t: str) -> str:
    """Normalize relation type to UPPER_SNAKE_CASE for Neo4j compatibility."""
    t = t.strip().upper()
    t = re.sub(r"[\s\-]+", "_", t)
    t = re.sub(r"[^A-Z0-9_]", "", t)
    if not t:
        t = "RELATED_TO"
    if t[0].isdigit():
        t = "_" + t
    return t


def get_driver(target: str = "yhoga"):
    """Resolve a driver via src.connection.Neo4jConnection (target='default' or 'yhoga')."""
    load_dotenv()
    # Make `src` importable when running this script directly
    repo_root = str(REPO)
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    from src.connection import Neo4jConnection

    try:
        conn = Neo4jConnection.by_name(target)
    except ValueError as e:
        sys.exit(str(e))
    print(f"-> Connecting to target='{target}' uri={conn.uri[:40]}...")
    return GraphDatabase.driver(conn.uri, auth=(conn.user, conn.password))


def count_state(session) -> dict:
    rs = session.run("""
        MATCH (n) WITH labels(n)[0] AS lbl, count(n) AS n
        RETURN collect({label: lbl, n: n}) AS nodes
    """)
    nodes = rs.single()["nodes"]
    rs = session.run("MATCH ()-[r]->() RETURN count(r) AS n")
    total_rels = rs.single()["n"]
    rs = session.run("""
        MATCH ()-[r]->() WITH type(r) AS t, count(r) AS n
        WHERE n >= 5
        RETURN collect({type: t, n: n}) AS top
    """)
    top = rs.single()["top"]
    return {
        "nodes": {x["label"]: x["n"] for x in nodes if x["label"]},
        "total_rels": total_rels,
        "top_rel_types": top,
    }


def wipe(session):
    session.run("MATCH (n) DETACH DELETE n")


def load_grades() -> dict[str, dict]:
    grades = {}
    for fname in GRADE_FILES:
        data = json.loads((SRC_DIR / fname).read_text(encoding="utf-8"))
        grades[data["grade"]] = data
    return grades


def collect_known_concepts(grades: dict) -> dict[str, set[str]]:
    known = defaultdict(set)
    for grade, data in grades.items():
        for ch in data["chapters"]:
            for st in ch.get("subtopics", []):
                for c in st.get("concepts", []):
                    known[grade].add(c["name"])
    return known


def ingest_structure(session, grade: str, data: dict):
    """Grade, Chapter, Subtopic, Concept + HAS_*, NEXT_CHAPTER."""
    session.run(
        "MERGE (g:Grade {name: $grade}) SET g.type = 'KLS_XII'",
        grade=grade,
    )

    for ch in data["chapters"]:
        session.run(
            """
            MERGE (g:Grade {name: $grade})
            MERGE (ch:Chapter {name: $chapter, grade: $grade})
            SET ch.summary = $summary
            MERGE (g)-[:HAS_CHAPTER]->(ch)
            """,
            grade=grade,
            chapter=ch["chapter"],
            summary=ch.get("chapter_summary", ""),
        )

    for ch in data["chapters"]:
        if ch.get("next"):
            session.run(
                """
                MATCH (a:Chapter {name: $a_name, grade: $grade}),
                      (b:Chapter {name: $b_name, grade: $grade})
                MERGE (a)-[:NEXT_CHAPTER]->(b)
                """,
                a_name=ch["chapter"],
                b_name=ch["next"],
                grade=grade,
            )

    for ch in data["chapters"]:
        for st in ch.get("subtopics", []):
            session.run(
                """
                MATCH (ch:Chapter {name: $chapter, grade: $grade})
                MERGE (st:Subtopic {name: $subtopic, chapter: $chapter, grade: $grade})
                SET st.provenance = $provenance
                MERGE (ch)-[:HAS_SUBTOPIC]->(st)
                """,
                chapter=ch["chapter"],
                subtopic=st["name"],
                grade=grade,
                provenance=st.get("provenance"),
            )
            for c in st.get("concepts", []):
                session.run(
                    """
                    MATCH (st:Subtopic {name: $subtopic, chapter: $chapter, grade: $grade})
                    MERGE (c:Concept {name: $name, grade: $grade})
                    SET c.description = $description,
                        c.glossary_validated = $gv,
                        c.materi_pokok_ref = $mpr,
                        c.provenance = $provenance
                    MERGE (st)-[:HAS_CONCEPT]->(c)
                    """,
                    subtopic=st["name"],
                    chapter=ch["chapter"],
                    grade=grade,
                    name=c["name"],
                    description=c.get("description", ""),
                    gv=bool(c.get("glossary_validated", False)),
                    mpr=c.get("materi_pokok_ref", ""),
                    provenance=c.get("provenance"),
                )


def ingest_chapter_relations(session, grade: str, data: dict) -> int:
    """Chapter-Chapter relations from chapter_relations[]. Returns count written."""
    count = 0
    for ch in data["chapters"]:
        for cr in ch.get("chapter_relations", []):
            rel_type = normalize_rel_type(cr["type"])
            session.run(
                f"""
                MATCH (a:Chapter {{name: $a_name, grade: $grade}}),
                      (b:Chapter {{name: $b_name, grade: $grade}})
                MERGE (a)-[r:`{rel_type}`]->(b)
                SET r.description = $description,
                    r.original_relation_type = $original_type
                """,
                a_name=ch["chapter"],
                b_name=cr["target_chapter"],
                grade=grade,
                description=cr.get("description", ""),
                original_type=cr["type"],
            )
            count += 1
    return count


def ingest_concept_relations(
    session, grade: str, data: dict, known_in_grade: set[str]
) -> tuple[int, int]:
    """Concept-level typed relations. Returns (n_to_concept, n_to_concept_target)."""
    n_concept = 0
    n_target = 0
    for ch in data["chapters"]:
        for st in ch.get("subtopics", []):
            for c in st.get("concepts", []):
                source = c["name"]
                for r in c.get("relations", []):
                    rel_type = normalize_rel_type(r["type"])
                    target = r["target"]
                    is_concept = target in known_in_grade
                    target_label = "Concept" if is_concept else "ConceptTarget"

                    ereview = r.get("expert_review") or {}
                    props = {
                        "description": r.get("description", ""),
                        "provenance": r.get("provenance"),
                        "original_type": r["type"],
                        "expert_status": ereview.get("status"),
                        "expert_consensus": ereview.get("consensus"),
                        "expert_n_reviewers": ereview.get("n_reviewers"),
                        "expert_review_json": json.dumps(
                            ereview, ensure_ascii=False
                        ) if ereview else None,
                    }

                    if not is_concept:
                        session.run(
                            "MERGE (t:ConceptTarget {name: $target, grade: $grade})",
                            target=target,
                            grade=grade,
                        )
                        n_target += 1
                    else:
                        n_concept += 1

                    session.run(
                        f"""
                        MATCH (a:Concept {{name: $source, grade: $grade}}),
                              (b:{target_label} {{name: $target, grade: $grade}})
                        MERGE (a)-[r:`{rel_type}`]->(b)
                        SET r.description = $description,
                            r.provenance = $provenance,
                            r.original_relation_type = $original_type,
                            r.expert_status = $expert_status,
                            r.expert_consensus = $expert_consensus,
                            r.expert_n_reviewers = $expert_n_reviewers,
                            r.expert_review_json = $expert_review_json
                        """,
                        source=source,
                        target=target,
                        grade=grade,
                        **props,
                    )
    return n_concept, n_target


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--target",
        default="yhoga",
        choices=["default", "yhoga", "soros"],
        help="Which Neo4j to write to. 'default'/'soros' = NEO4J_URI, "
             "'yhoga' = NEO4J_URI_YHOGA. Default: yhoga (legacy).",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Connect, print BEFORE state, then exit without wiping or writing.",
    )
    args = ap.parse_args()

    driver = get_driver(args.target)
    grades = load_grades()
    known_concepts = collect_known_concepts(grades)

    print(f"Loaded {len(grades)} grades from {SRC_DIR}")
    for g, ks in known_concepts.items():
        print(f"  {g}: {len(ks)} distinct concept names")

    with driver.session() as session:
        print("\n=== BEFORE ===")
        before = count_state(session)
        print(f"  Nodes: {before['nodes']}")
        print(f"  Total relationships: {before['total_rels']}")

        if args.dry_run:
            print("\n--dry-run set, exiting without writes.")
            driver.close()
            return 0

        print("\n=== WIPING (destructive) ===")
        wipe(session)
        after_wipe = count_state(session)
        print(f"  After wipe - nodes: {after_wipe['nodes']}, rels: {after_wipe['total_rels']}")
        assert after_wipe["total_rels"] == 0, "wipe did not remove all relationships"

        print("\n=== INGEST: structure (Grade/Chapter/Subtopic/Concept + HAS_*) ===")
        for grade, data in grades.items():
            ingest_structure(session, grade, data)
            print(f"  {grade}: structure done")

        print("\n=== INGEST: chapter_relations (Chapter to Chapter) ===")
        total_chrels = 0
        for grade, data in grades.items():
            n = ingest_chapter_relations(session, grade, data)
            print(f"  {grade}: {n} chapter relations")
            total_chrels += n
        print(f"  Total chapter-level rels: {total_chrels}")

        print("\n=== INGEST: concept relations (with expert_review) ===")
        total_to_concept = 0
        total_to_target = 0
        for grade, data in grades.items():
            nc, nt = ingest_concept_relations(
                session, grade, data, known_concepts[grade]
            )
            print(f"  {grade}: {nc} -> Concept, {nt} -> ConceptTarget")
            total_to_concept += nc
            total_to_target += nt
        print(f"  Total concept rels: {total_to_concept} -> Concept, {total_to_target} -> ConceptTarget")

        print("\n=== AFTER ===")
        after = count_state(session)
        print(f"  Nodes: {after['nodes']}")
        print(f"  Total relationships: {after['total_rels']}")
        print(f"  Top rel types (n>=5):")
        for r in sorted(after["top_rel_types"], key=lambda x: -x["n"]):
            print(f"    {r['type']:35} {r['n']:>5}")

    driver.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
