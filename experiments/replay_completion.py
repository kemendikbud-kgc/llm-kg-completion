"""Replay a staged LINTAS_BUKU_* completion JSON into the Yhoga Aura instance.

Reads the friend-llm-shaped JSON produced by Step 5 of pages/5_Completion.py
(or experiments/dump_lintas_buku.py) and MERGEs each edge into Yhoga, keyed by
(Concept.name, Concept.grade). Idempotent: re-running on the same JSON
produces no schema or count change beyond what's already there.

Usage:
    python experiments/replay_completion.py [path/to/lintas_buku_edges.json] [--dry-run]

If no path is given, defaults to:
    experiments/knowledge_graph_states/completion-experiments/ann-classifier-v1/lintas_buku_edges.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase

DEFAULT_INPUT = (
    Path(__file__).resolve().parent
    / "knowledge_graph_states"
    / "completion-experiments"
    / "ann-classifier-v1"
    / "lintas_buku_edges.json"
)

ALLOWED_TYPES = frozenset(
    {
        "LINTAS_BUKU_SAMA_DENGAN",
        "LINTAS_BUKU_APLIKASI_DARI",
        "LINTAS_BUKU_PRASYARAT_UNTUK",
        "LINTAS_BUKU_MEMPERDALAM",
        "LINTAS_BUKU_BERKAITAN_DENGAN",
    }
)


def _validate_edge(edge: dict) -> tuple[bool, str]:
    rt = edge.get("rel_type", "")
    if rt not in ALLOWED_TYPES:
        return False, f"unknown rel_type {rt!r} (not in canonical 5-set)"
    for key in ("source_name", "source_grade", "target_name", "target_grade"):
        if not edge.get(key):
            return False, f"missing {key}"
    if edge["source_grade"] == edge["target_grade"]:
        return False, "source_grade == target_grade (LINTAS_BUKU is cross-book only)"
    return True, ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input",
        nargs="?",
        default=str(DEFAULT_INPUT),
        help=f"Path to lintas_buku_edges.json (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Count what would be merged, but do not write to Neo4j.",
    )
    args = parser.parse_args()

    in_path = Path(args.input)
    if not in_path.is_file():
        sys.stderr.write(f"ERROR: input file not found: {in_path}\n")
        return 2

    doc = json.loads(in_path.read_text(encoding="utf-8"))
    edges = doc.get("edges", [])
    if not isinstance(edges, list) or not edges:
        sys.stderr.write(f"ERROR: no edges in {in_path}\n")
        return 2

    valid: list[dict] = []
    skipped: list[tuple[dict, str]] = []
    for e in edges:
        ok, reason = _validate_edge(e)
        if ok:
            valid.append(e)
        else:
            skipped.append((e, reason))

    print(
        f"Loaded {len(edges)} edges from {in_path.name} "
        f"({len(valid)} valid, {len(skipped)} skipped)"
    )
    if skipped:
        print("First 5 skipped edges:")
        for e, reason in skipped[:5]:
            print(
                f"  - {e.get('rel_type', '?')}: "
                f"{e.get('source_name', '?')} -> {e.get('target_name', '?')}: {reason}"
            )

    breakdown: dict[str, int] = {}
    for e in valid:
        breakdown[e["rel_type"]] = breakdown.get(e["rel_type"], 0) + 1
    print("Edge type breakdown (valid):")
    for rt, n in sorted(breakdown.items(), key=lambda kv: -kv[1]):
        print(f"  {rt:34s} {n:>4d}")

    if args.dry_run:
        print(f"\nDRY RUN: would MERGE {len(valid)} edges into Yhoga. No writes performed.")
        return 0

    load_dotenv()
    uri = os.getenv("NEO4J_URI_YHOGA")
    user = os.getenv("NEO4J_USERNAME_YHOGA", "neo4j")
    pwd = os.getenv("NEO4J_PASSWORD_YHOGA")
    if not uri or not pwd:
        sys.stderr.write(
            "ERROR: NEO4J_URI_YHOGA and NEO4J_PASSWORD_YHOGA must be set in .env\n"
        )
        return 2

    # Group by rel_type so we can use a single parameterized MERGE per type
    # (Cypher does not allow rel-type as a parameter; one query per type is
    # idiomatic and keeps the merge count cheap).
    by_type: dict[str, list[dict]] = {}
    for e in valid:
        by_type.setdefault(e["rel_type"], []).append(e)

    written = 0
    with GraphDatabase.driver(uri, auth=(user, pwd)) as driver:
        for rel_type, type_edges in by_type.items():
            payload = [
                {
                    "src": e["source_name"],
                    "src_grade": e["source_grade"],
                    "tgt": e["target_name"],
                    "tgt_grade": e["target_grade"],
                    "description": e.get("properties", {}).get("description", ""),
                    "confidence": float(
                        e.get("properties", {}).get("confidence", 0.0)
                    ),
                    "method": e.get("properties", {}).get(
                        "method", doc.get("version", "ann-classifier-v1")
                    ),
                }
                for e in type_edges
            ]
            cypher = f"""
                UNWIND $rows AS row
                MATCH (a:Concept {{name: row.src, grade: row.src_grade}})
                MATCH (b:Concept {{name: row.tgt, grade: row.tgt_grade}})
                MERGE (a)-[r:{rel_type}]->(b)
                SET r.description = row.description,
                    r.confidence = row.confidence,
                    r.method = row.method
                RETURN count(r) AS merged
            """
            with driver.session() as session:
                result = session.run(cypher, rows=payload).single()
                merged_n = result["merged"] if result else 0
            print(f"  MERGE {rel_type:34s} {merged_n:>4d} / {len(type_edges)} payloaded")
            written += merged_n

        # Sanity: total LINTAS_BUKU_* edges in Yhoga after replay.
        with driver.session() as session:
            r = session.run(
                "MATCH ()-[r]->() WHERE type(r) STARTS WITH 'LINTAS_BUKU' "
                "RETURN count(r) AS n"
            ).single()
            total_now = r["n"] if r else 0

    print(f"\nWrote/updated {written} LINTAS_BUKU_* edges.")
    print(f"Total LINTAS_BUKU_* edges in Yhoga now: {total_now}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
