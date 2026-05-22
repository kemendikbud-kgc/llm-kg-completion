"""Resolve every reviewer index back to a concrete triple, and emit an audit table.

Reads:
  - data/expert_feedback/redis_snapshot_<date>/courses/kg__courses.json
  - data/expert_feedback/redis_snapshot_<date>/reviewers/*.json

Writes:
  - data/expert_feedback/redis_snapshot_<date>/resolved/triples_<course>.json
        Flattened triple list per course, with index, source/target, type, etc.
  - data/expert_feedback/redis_snapshot_<date>/resolved/feedback_resolved.json
        Every rating/comment/missing-triple joined to its triple.
  - data/expert_feedback/redis_snapshot_<date>/resolved/summary.md
        Human-readable audit of what would be applied to the KG.

Read-only: hits no DB, only files in this snapshot directory.

USAGE: python experiments/scripts/resolve_expert_feedback.py [snapshot_dir]
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


def find_latest_snapshot() -> Path:
    base = Path("data/expert_feedback")
    candidates = sorted(
        p for p in base.glob("redis_snapshot_*") if p.is_dir()
    )
    if not candidates:
        sys.exit("No redis_snapshot_* directory found under data/expert_feedback/")
    return candidates[-1]


def flatten_course_triples(payload: dict) -> list[dict]:
    """Flatten a course's relations in canonical (depth-first) order.

    Returns a list where item i = the i-th triple in the same order
    the kg-review-app's reviewer indices reference.
    """
    triples = []
    for ch in payload.get("chapters", []):
        chapter = ch["chapter"]
        for st in ch.get("subtopics", []):
            subtopic = st["name"]
            for c in st.get("concepts", []):
                source = c["name"]
                source_description = c.get("description", "")
                for r in c.get("relations", []):
                    triples.append(
                        {
                            "index": len(triples),
                            "chapter": chapter,
                            "subtopic": subtopic,
                            "source_concept": source,
                            "source_description": source_description,
                            "relation_type": r["type"],
                            "target": r["target"],
                            "description": r.get("description", ""),
                        }
                    )
    return triples


def main() -> int:
    snap = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else find_latest_snapshot()
    )
    print(f"Using snapshot: {snap}")

    courses_data = json.loads(
        (snap / "courses" / "kg__courses.json").read_text(encoding="utf-8")
    )

    # Build {course_id: flattened_triples}
    course_triples: dict[str, list[dict]] = {}
    course_grade: dict[str, str] = {}
    for course in courses_data:
        cid = course["id"]
        course_grade[cid] = course["grade"]
        course_triples[cid] = flatten_course_triples(course["payload"])

    resolved_dir = snap / "resolved"
    resolved_dir.mkdir(exist_ok=True)
    for cid, triples in course_triples.items():
        out = resolved_dir / f"triples_{cid}.json"
        out.write_text(
            json.dumps(triples, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"  Wrote {len(triples):>4} triples -> resolved/{out.name}")

    # Join reviewer feedback to triples
    per_triple: dict[tuple[str, int], dict] = {}
    all_missing: list[dict] = []
    general_feedback: list[dict] = []

    reviewers_dir = snap / "reviewers"
    for f in sorted(reviewers_dir.glob("*.json")):
        reviewer, course = f.stem.split("__", 1)
        d = json.loads(f.read_text(encoding="utf-8"))
        triples = course_triples.get(course, [])
        if not triples:
            print(f"  WARN: no triples for course {course} (reviewer {reviewer})")
            continue

        for idx_str, rating in (d.get("ratings") or {}).items():
            idx = int(idx_str)
            if idx >= len(triples):
                print(f"  WARN: {reviewer} idx {idx} >= {len(triples)} on {course}")
                continue
            key = (course, idx)
            entry = per_triple.setdefault(
                key,
                {
                    "course": course,
                    "grade": course_grade[course],
                    "index": idx,
                    "triple": triples[idx],
                    "ratings": {},  # reviewer -> rating
                    "comments": {},  # reviewer -> comment
                },
            )
            entry["ratings"][reviewer] = rating

        for idx_str, comment in (d.get("comments") or {}).items():
            idx = int(idx_str)
            if idx >= len(triples):
                continue
            key = (course, idx)
            entry = per_triple.setdefault(
                key,
                {
                    "course": course,
                    "grade": course_grade[course],
                    "index": idx,
                    "triple": triples[idx],
                    "ratings": {},
                    "comments": {},
                },
            )
            entry["comments"][reviewer] = comment

        for mt in (d.get("missingTriples") or []):
            all_missing.append(
                {"reviewer": reviewer, "course": course, "grade": course_grade[course], **mt}
            )

        gf = d.get("generalFeedback") or ""
        if gf.strip():
            general_feedback.append(
                {"reviewer": reviewer, "course": course, "feedback": gf}
            )

    # Compute consensus + actions per triple
    resolved_entries = []
    for (course, idx), entry in sorted(per_triple.items()):
        ratings = entry["ratings"]
        counts = Counter(ratings.values())
        n = sum(counts.values())
        # consensus = majority rating; ties broken by precedence
        precedence = ["correct", "partial", "wrong", "missing"]
        consensus = max(
            counts, key=lambda r: (counts[r], -precedence.index(r))
        ) if counts else None

        # Recommended action
        if consensus == "correct":
            action = "keep"
        elif consensus == "partial":
            action = "flag-partial"
        elif consensus == "wrong":
            action = "drop-or-fix"
        elif consensus == "missing":
            action = "needs-context"
        else:
            action = "comment-only" if entry["comments"] else "unknown"

        resolved_entries.append(
            {
                **entry,
                "n_reviewers": n,
                "rating_counts": dict(counts),
                "consensus": consensus,
                "action": action,
            }
        )

    feedback_resolved = {
        "snapshot_dir": str(snap),
        "courses": {
            cid: {"grade": course_grade[cid], "n_triples": len(t)}
            for cid, t in course_triples.items()
        },
        "n_triples_with_feedback": len(resolved_entries),
        "n_missing_triples_proposed": len(all_missing),
        "n_general_feedback_notes": len(general_feedback),
        "per_triple_feedback": resolved_entries,
        "missing_triples": all_missing,
        "general_feedback": general_feedback,
    }
    out = resolved_dir / "feedback_resolved.json"
    out.write_text(
        json.dumps(feedback_resolved, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nWrote feedback_resolved.json with {len(resolved_entries)} reviewed triples")

    # Per-course action summary
    by_course_action: dict[str, Counter] = defaultdict(Counter)
    by_course_overlap: dict[str, list[int]] = defaultdict(list)
    for e in resolved_entries:
        by_course_action[e["course"]][e["action"]] += 1
        by_course_overlap[e["course"]].append(e["n_reviewers"])
    by_missing: Counter = Counter(m["course"] for m in all_missing)

    # Human summary
    lines = []
    lines.append("# Expert Feedback — Resolved Audit\n")
    lines.append(f"Snapshot: `{snap.name}`\n")
    lines.append("## Per-course summary\n")
    lines.append("| Course | Triples | Triples w/ feedback | Multi-reviewer overlap | Missing triples proposed |")
    lines.append("|---|---:|---:|---:|---:|")
    for cid, triples in course_triples.items():
        n_with_fb = sum(
            1 for e in resolved_entries if e["course"] == cid
        )
        overlap = sum(1 for n in by_course_overlap[cid] if n >= 2)
        lines.append(
            f"| `{course_grade[cid]}` | {len(triples)} | {n_with_fb} | {overlap} | {by_missing.get(cid, 0)} |"
        )

    lines.append("\n## Recommended action distribution\n")
    lines.append("| Course | keep | flag-partial | drop-or-fix | needs-context | comment-only |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for cid in course_triples:
        c = by_course_action[cid]
        lines.append(
            f"| `{course_grade[cid]}` | {c.get('keep',0)} | {c.get('flag-partial',0)} "
            f"| {c.get('drop-or-fix',0)} | {c.get('needs-context',0)} | {c.get('comment-only',0)} |"
        )

    lines.append("\n## Reviewer-proposed missing triples by course\n")
    miss_by_course: dict[str, list[dict]] = defaultdict(list)
    for m in all_missing:
        miss_by_course[m["course"]].append(m)
    for cid, items in miss_by_course.items():
        lines.append(f"\n### {course_grade[cid]} ({len(items)} missing triples)\n")
        for m in items:
            lines.append(
                f"- **{m['subject']}** -[{m['relation']}]-> **{m['target']}**"
                f"  (chapter: {m['chapter']}, by {m['reviewer']})"
            )
            if m.get("description"):
                lines.append(f"  - {m['description']}")

    lines.append("\n## General feedback notes\n")
    for gf in general_feedback:
        lines.append(f"- **{gf['reviewer']}** ({gf['course']}):")
        for line in gf["feedback"].splitlines():
            lines.append(f"  > {line}")

    (resolved_dir / "summary.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )
    print(f"Wrote summary.md -> {resolved_dir / 'summary.md'}")

    print("\nTop-line numbers:")
    print(f"  Triples with any feedback: {len(resolved_entries)}")
    print(f"  Triples with multi-reviewer overlap: "
          f"{sum(1 for e in resolved_entries if e['n_reviewers']>=2)}")
    print(f"  Reviewer-proposed missing triples: {len(all_missing)}")
    print(f"  General feedback notes: {len(general_feedback)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
