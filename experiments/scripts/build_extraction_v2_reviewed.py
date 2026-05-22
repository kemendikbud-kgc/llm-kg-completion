"""Build extraction-v2-reviewed from extraction-v1 + expert feedback.

Reads:
  - experiments/knowledge_graph_states/extraction-v1/{Biologi,Fisika,Kimia} Kelas XII.json
  - data/expert_feedback/redis_snapshot_<date>/resolved/feedback_resolved.json

Writes (all under experiments/knowledge_graph_states/extraction-v2-reviewed/):
  - {Biologi,Fisika,Kimia} Kelas XII.json   — merged v1 + expert annotations + 29 added Kimia triples
  - operations_log.json                      — every per-triple decision traced back to reviewer source
  - dropped_triples.json                     — the 5 consensus-wrong triples removed, with rationale
  - manifest.json                            — counts + provenance for the build

Per-relation annotation schema added to extraction-v2-reviewed:
    "expert_review": {
        "status": "correct" | "partial" | "wrong" | "missing" | null,
        "consensus": <same domain>,
        "n_reviewers": int,
        "ratings": {reviewer: rating},
        "comments": {reviewer: comment}
    }

Reviewer-proposed missing triples are appended under each chapter as a synthetic
subtopic "Expert Proposed Triples" so they're visually grouped and obvious.

Read-only on inputs, no DB access. USAGE:
    python experiments/scripts/build_extraction_v2_reviewed.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC_DIR = REPO / "experiments" / "knowledge_graph_states" / "extraction-v1"
OUT_DIR = REPO / "experiments" / "knowledge_graph_states" / "extraction-v2-reviewed"
FEEDBACK_BASE = REPO / "data" / "expert_feedback"


def find_latest_snapshot() -> Path:
    candidates = sorted(p for p in FEEDBACK_BASE.glob("redis_snapshot_*") if p.is_dir())
    if not candidates:
        sys.exit("No redis_snapshot_* directory found.")
    return candidates[-1]


def load_resolved_feedback(snap: Path) -> dict:
    p = snap / "resolved" / "feedback_resolved.json"
    if not p.exists():
        sys.exit(f"Missing {p}. Run experiments/scripts/resolve_expert_feedback.py first.")
    return json.loads(p.read_text(encoding="utf-8"))


def flatten_index_iter(payload: dict):
    """Yield (idx, chapter_idx, subtopic_idx, concept_idx, relation_idx) for every relation
    in canonical depth-first order. Matches reviewer triple indices."""
    idx = 0
    for ci, ch in enumerate(payload.get("chapters", [])):
        for si, st in enumerate(ch.get("subtopics", [])):
            for ki, c in enumerate(st.get("concepts", [])):
                for ri, _ in enumerate(c.get("relations", [])):
                    yield idx, ci, si, ki, ri
                    idx += 1


def build_v3():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    snap = find_latest_snapshot()
    feedback = load_resolved_feedback(snap)
    print(f"Using feedback snapshot: {snap.name}")

    # Index per-triple feedback by (grade, index)
    per_triple_by_grade: dict[str, dict[int, dict]] = defaultdict(dict)
    for e in feedback["per_triple_feedback"]:
        per_triple_by_grade[e["grade"]][e["index"]] = e

    # Index missing triples by (grade, chapter, subject)
    missing_by_chapter: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for m in feedback["missing_triples"]:
        missing_by_chapter[(m["grade"], m["chapter"])].append(m)

    grades = ["Biologi Kelas XII", "Fisika Kelas XII", "Kimia Kelas XII"]
    operations: list[dict] = []
    dropped: list[dict] = []
    grade_counts: dict[str, dict] = {}

    for grade in grades:
        v1_path = SRC_DIR / f"{grade}.json"
        v3_path = OUT_DIR / f"{grade}.json"
        data = json.loads(v1_path.read_text(encoding="utf-8"))
        assert data["grade"] == grade, f"grade mismatch in {v1_path}"

        index_lookup = list(flatten_index_iter(data))
        feedback_for_grade = per_triple_by_grade.get(grade, {})

        # Collect per-relation actions and apply in a SECOND pass, because deletions
        # change indices if we modify in place during the walk.
        n_keep = n_drop = n_partial = n_needs_context = n_annotated_only = 0
        relations_to_drop: set[tuple[int, int, int, int]] = set()
        per_relation_annotation: dict[tuple[int, int, int, int], dict] = {}

        for idx, ci, si, ki, ri in index_lookup:
            fb = feedback_for_grade.get(idx)
            ch = data["chapters"][ci]
            st = ch["subtopics"][si]
            cpt = st["concepts"][ki]
            rel = cpt["relations"][ri]
            triple_desc = {
                "grade": grade,
                "chapter": ch["chapter"],
                "subtopic": st["name"],
                "source_concept": cpt["name"],
                "relation_type": rel["type"],
                "target": rel["target"],
                "description": rel.get("description", ""),
                "triple_index": idx,
            }

            if not fb:
                # No reviewer touched this triple. Keep as-is, no annotation.
                operations.append({**triple_desc, "operation": "keep", "reason": "no feedback"})
                n_keep += 1
                continue

            status = fb.get("consensus")
            action = fb.get("action")
            if action == "drop-or-fix":
                # Honor the drop. The 5 wrong-consensus triples land here.
                relations_to_drop.add((ci, si, ki, ri))
                drop_entry = {
                    **triple_desc,
                    "consensus": status,
                    "n_reviewers": fb["n_reviewers"],
                    "rating_counts": fb["rating_counts"],
                    "ratings": fb["ratings"],
                    "comments": fb["comments"],
                    "rationale": (
                        f"Consensus rating 'wrong' from "
                        f"{fb['n_reviewers']} reviewer(s). Honoring single-reviewer drops "
                        "per build policy; reviewer identities recorded for audit."
                    ),
                }
                dropped.append(drop_entry)
                operations.append({**triple_desc, "operation": "drop", "consensus": status})
                n_drop += 1
                continue

            # Otherwise keep + annotate
            annotation = {
                "status": status,
                "consensus": status,
                "n_reviewers": fb["n_reviewers"],
                "ratings": fb["ratings"],
                "comments": fb["comments"],
            }
            per_relation_annotation[(ci, si, ki, ri)] = annotation
            op = {"keep": "keep+annotate", "flag-partial": "flag-partial",
                  "needs-context": "needs-context", "comment-only": "annotate-comment"}.get(action, "annotate")
            operations.append({**triple_desc, "operation": op, "consensus": status})
            if action == "flag-partial":
                n_partial += 1
            elif action == "needs-context":
                n_needs_context += 1
            else:
                n_annotated_only += 1

        # Second pass: rebuild the chapter structure with drops removed + annotations applied
        for ci, ch in enumerate(data["chapters"]):
            for si, st in enumerate(ch["subtopics"]):
                for ki, cpt in enumerate(st["concepts"]):
                    new_rels = []
                    for ri, rel in enumerate(cpt["relations"]):
                        if (ci, si, ki, ri) in relations_to_drop:
                            continue
                        ann = per_relation_annotation.get((ci, si, ki, ri))
                        if ann:
                            rel = {**rel, "expert_review": ann}
                        new_rels.append(rel)
                    cpt["relations"] = new_rels

        # Append reviewer-proposed missing triples per chapter
        n_added = 0
        for ci, ch in enumerate(data["chapters"]):
            chapter_name = ch["chapter"]
            proposed = missing_by_chapter.get((grade, chapter_name), [])
            if not proposed:
                continue
            # Group proposed triples by source-concept (`subject`)
            by_source: dict[str, list[dict]] = defaultdict(list)
            for m in proposed:
                by_source[m["subject"]].append(m)
            new_concepts = []
            for source_name, items in by_source.items():
                relations_payload = [
                    {
                        "type": m["relation"],
                        "target": m["target"],
                        "description": m.get("description", "") or "",
                        "provenance": "expert-proposed",
                        "expert_review": {
                            "status": "proposed",
                            "consensus": "proposed",
                            "n_reviewers": 1,
                            "ratings": {m["reviewer"]: "proposed"},
                            "comments": {},
                        },
                    }
                    for m in items
                ]
                new_concepts.append(
                    {
                        "name": source_name,
                        "description": "",
                        "glossary_validated": False,
                        "materi_pokok_ref": "",
                        "relations": relations_payload,
                        "provenance": "expert-proposed",
                    }
                )
                n_added += len(items)
                for m, rel_p in zip(items, relations_payload):
                    operations.append(
                        {
                            "grade": grade,
                            "chapter": chapter_name,
                            "subtopic": "Expert Proposed Triples",
                            "source_concept": source_name,
                            "relation_type": m["relation"],
                            "target": m["target"],
                            "description": rel_p["description"],
                            "triple_index": None,
                            "operation": "add",
                            "consensus": "proposed",
                            "reviewer": m["reviewer"],
                        }
                    )
            if new_concepts:
                ch.setdefault("subtopics", []).append(
                    {
                        "name": "Expert Proposed Triples",
                        "concepts": new_concepts,
                        "provenance": "expert-proposed",
                    }
                )

        # Write v3 file for this grade
        v3_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        grade_counts[grade] = {
            "kept": n_keep + n_partial + n_needs_context + n_annotated_only,
            "dropped": n_drop,
            "annotated_correct": n_annotated_only,
            "annotated_partial": n_partial,
            "annotated_needs_context": n_needs_context,
            "added": n_added,
        }
        print(
            f"  {grade}: kept={grade_counts[grade]['kept']}, "
            f"dropped={n_drop}, added={n_added}, "
            f"annot_partial={n_partial}, annot_needs_context={n_needs_context}"
        )

    # Write operations log
    (OUT_DIR / "operations_log.json").write_text(
        json.dumps(
            {
                "built_at": date.today().isoformat(),
                "feedback_snapshot": snap.name,
                "policy": {
                    "drop_threshold": "single-reviewer 'wrong' is honored (recorded in dropped_triples.json for review)",
                    "comment_handling": "comments stored as annotation only; do not override rating",
                    "proposed_triples": "appended per chapter under synthetic 'Expert Proposed Triples' subtopic",
                },
                "operations": operations,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    # Write dropped triples
    (OUT_DIR / "dropped_triples.json").write_text(
        json.dumps(
            {
                "built_at": date.today().isoformat(),
                "feedback_snapshot": snap.name,
                "policy_note": (
                    "These 5 triples were rated 'wrong' by expert reviewers and removed "
                    "from v3-canonical-pre-completion. Single-reviewer drops are honored "
                    "(the reviewer is the only domain expert who reviewed that course). "
                    "Each drop preserves the original triple, the reviewer ratings/comments, "
                    "and the rationale below so the friend/team can audit or override."
                ),
                "n_dropped": len(dropped),
                "dropped": dropped,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    # Aggregate counts
    op_counter = Counter(o["operation"] for o in operations)
    manifest = {
        "version": "extraction-v2-reviewed",
        "source_state": "extraction-v1",
        "built_at": date.today().isoformat(),
        "feedback_snapshot": snap.name,
        "per_grade": grade_counts,
        "totals": {
            "operations": dict(op_counter),
            "n_dropped": len(dropped),
        },
        "policy": {
            "single_reviewer_drops": "honored",
            "comment_handling": "flag-only (annotation, no rating override)",
        },
    }
    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("\nManifest summary:")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(build_v3())
