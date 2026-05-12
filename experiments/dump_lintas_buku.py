"""Dump every LINTAS_BUKU_* edge from the Yhoga Aura instance to JSON.

Usage:
    python experiments/dump_lintas_buku.py [output_path]

Default output: experiments/knowledge_graph_states/v2-friend-completion-llm/lintas_buku_edges.json

The dump is text-diffable, replayable into any Neo4j via UNWIND+MERGE, and
serves as the auditable text-form record of the cross-book completion state
(belt-and-suspenders alongside the binary .backup).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from datetime import date

from dotenv import load_dotenv
from neo4j import GraphDatabase

DEFAULT_OUT = (
    Path(__file__).resolve().parent
    / "knowledge_graph_states"
    / "v2-friend-completion-llm"
    / "lintas_buku_edges.json"
)


def main() -> int:
    load_dotenv()
    uri = os.getenv("NEO4J_URI_YHOGA")
    user = os.getenv("NEO4J_USERNAME_YHOGA", "neo4j")
    pwd = os.getenv("NEO4J_PASSWORD_YHOGA")
    if not uri or not pwd:
        sys.stderr.write(
            "ERROR: NEO4J_URI_YHOGA and NEO4J_PASSWORD_YHOGA must be set in .env\n"
        )
        return 2

    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT
    out_path.parent.mkdir(parents=True, exist_ok=True)

    counts_query = """
        MATCH (n) RETURN labels(n)[0] AS label, count(n) AS n
    """
    edges_query = """
        MATCH (a)-[r]->(b) WHERE type(r) STARTS WITH 'LINTAS_BUKU'
        RETURN type(r) AS rel_type,
               labels(a)[0] AS source_label, a.name AS source_name, a.grade AS source_grade,
               labels(b)[0] AS target_label, b.name AS target_name, b.grade AS target_grade,
               properties(r) AS properties
        ORDER BY type(r), a.name, b.name
    """
    total_rels_query = "MATCH ()-[r]->() RETURN count(r) AS total_rels"

    with GraphDatabase.driver(uri, auth=(user, pwd)) as driver, driver.session() as session:
        node_counts = {r["label"]: r["n"] for r in session.run(counts_query)}
        edges = [dict(r) for r in session.run(edges_query)]
        total_rels = session.run(total_rels_query).single()["total_rels"]

    breakdown: dict[str, int] = {}
    for e in edges:
        breakdown[e["rel_type"]] = breakdown.get(e["rel_type"], 0) + 1

    doc = {
        "version": "v2-friend-completion-llm",
        "source_state": "v1-extraction",
        "date_captured": date.today().isoformat(),
        "captured_from": "Yhoga Neo4j Aura Free instance",
        "instance_counts_at_capture": {
            **node_counts,
            "total_relationships": total_rels,
        },
        "edge_count": len(edges),
        "edge_type_breakdown": dict(
            sorted(breakdown.items(), key=lambda kv: -kv[1])
        ),
        "edges": edges,
    }

    out_path.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"Wrote {len(edges)} edges across {len(breakdown)} types to {out_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
