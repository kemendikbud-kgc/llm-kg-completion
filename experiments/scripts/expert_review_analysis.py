"""
Expert review analysis for KG validation.

Loads JSON files exported from the KG Review App and computes:
  - per-file rating distribution (correct / partial / wrong / missing)
  - precision and recall per the thesis formulas
  - Cohen's kappa for any pair of reviewers covering the same subject+chapter

Usage:
  uv run python experiments/scripts/expert_review_analysis.py [input_dir]

If input_dir is omitted, defaults to the Downloads folder where the export lives.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

DEFAULT_INPUT_DIR = Path(
    r"C:\Users\Soros\Downloads\Feedback-20260506T040248Z-3-001\Feedback"
)

# Filename grammar: expert-<subject>-<bab>[-<reviewer_tag>].json
# Examples:
#   expert-biologi-1.json            -> subject=biologi, bab=1, reviewer=None
#   expert-fisika-2-kimia.json       -> subject=fisika,  bab=2, reviewer=kimia
FILENAME_RE = re.compile(
    r"^expert-(?P<subject>[a-z]+)-(?P<bab>\d+)(?:-(?P<reviewer>[a-z0-9]+))?\.json$",
    re.IGNORECASE,
)


def parse_filename(name: str) -> dict | None:
    m = FILENAME_RE.match(name)
    if not m:
        return None
    return {
        "subject": m["subject"].lower(),
        "bab": int(m["bab"]),
        "reviewer": (m["reviewer"] or "default").lower(),
    }


def compute_metrics(ratings: dict[str, str], n_added_missing: int) -> dict:
    """Precision / recall per the thesis formulas.

    Precision = (correct + 0.5 * partial) / total_rated
    Recall    = (correct + 0.5 * partial) / (total_rated + n_added_missing)

    The "missing" rating value (kurang konteks) is counted in totals but does
    not contribute to the numerator. n_added_missing is the size of the
    reviewer's missingTriples[] array (not the count of "missing" ratings).
    """
    counts = Counter(ratings.values())
    total = sum(counts.values())
    correct = counts.get("correct", 0)
    partial = counts.get("partial", 0)
    wrong = counts.get("wrong", 0)
    missing_rating = counts.get("missing", 0)

    numerator = correct + 0.5 * partial
    precision = numerator / total if total else float("nan")
    recall_denom = total + n_added_missing
    recall = numerator / recall_denom if recall_denom else float("nan")

    return {
        "total": total,
        "correct": correct,
        "partial": partial,
        "wrong": wrong,
        "missing_rating": missing_rating,
        "added_missing": n_added_missing,
        "precision": precision,
        "recall": recall,
    }


def cohen_kappa(a: list[str], b: list[str]) -> float | None:
    if not a or len(a) != len(b):
        return None
    n = len(a)
    categories = sorted(set(a) | set(b))
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    pe = sum(
        (a.count(k) / n) * (b.count(k) / n) for k in categories
    )
    if pe == 1:
        return 1.0 if po == 1 else float("nan")
    return (po - pe) / (1 - pe)


def main(input_dir: Path) -> int:
    files = sorted(input_dir.glob("expert-*.json"))
    if not files:
        print(f"No expert-*.json files found in {input_dir}")
        return 1

    rows = []
    parsed_by_chapter = defaultdict(list)  # (subject, bab) -> [(reviewer, ratings)]

    for path in files:
        meta = parse_filename(path.name)
        if not meta:
            print(f"  SKIP (cannot parse name): {path.name}")
            continue
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        ratings = data.get("ratings", {})
        added_missing = len(data.get("missingTriples", []) or [])
        metrics = compute_metrics(ratings, added_missing)
        row = {
            "file": path.name,
            "subject": meta["subject"],
            "bab": meta["bab"],
            "reviewer": meta["reviewer"],
            **metrics,
        }
        rows.append(row)
        parsed_by_chapter[(meta["subject"], meta["bab"])].append(
            (meta["reviewer"], ratings)
        )

    # ----- Per-file table -----
    print("\n=== Per-file Metrics ===")
    header = (
        f"{'file':40}{'n':>5}{'C':>5}{'P':>5}{'W':>5}{'M':>5}"
        f"{'+miss':>7}{'prec':>8}{'rec':>8}"
    )
    print(header)
    print("-" * len(header))
    for r in rows:
        print(
            f"{r['file']:40}"
            f"{r['total']:>5}"
            f"{r['correct']:>5}"
            f"{r['partial']:>5}"
            f"{r['wrong']:>5}"
            f"{r['missing_rating']:>5}"
            f"{r['added_missing']:>7}"
            f"{r['precision']:>8.3f}"
            f"{r['recall']:>8.3f}"
        )
    print(
        "\nLegend: n=total rated, C=correct, P=partial, W=wrong, "
        "M=missing-rating (kurang konteks), +miss=missingTriples added.\n"
        "prec = (C + 0.5P) / n,  rec = (C + 0.5P) / (n + +miss)"
    )

    # ----- Cohen's kappa where pairs exist -----
    print("\n=== Inter-rater Agreement (Cohen's kappa) ===")
    found_pair = False
    for (subject, bab), entries in parsed_by_chapter.items():
        if len(entries) < 2:
            continue
        found_pair = True
        for i in range(len(entries)):
            for j in range(i + 1, len(entries)):
                ra, rb = entries[i], entries[j]
                # Only triples both rated
                shared_keys = sorted(set(ra[1]) & set(rb[1]))
                a_vals = [ra[1][k] for k in shared_keys]
                b_vals = [rb[1][k] for k in shared_keys]
                kappa = cohen_kappa(a_vals, b_vals)
                print(
                    f"  {subject:8} bab {bab}: "
                    f"{ra[0]} <-> {rb[0]}  shared={len(shared_keys)}  "
                    f"kappa={kappa:.3f}" if kappa is not None else "kappa=NA"
                )
    if not found_pair:
        print(
            "  (no reviewer pairs cover the same subject+chapter — "
            "kappa cannot be computed with current data)"
        )

    # ----- Summary by subject -----
    print("\n=== Aggregated by Subject ===")
    by_subject = defaultdict(lambda: Counter())
    for r in rows:
        by_subject[r["subject"]]["total"] += r["total"]
        by_subject[r["subject"]]["correct"] += r["correct"]
        by_subject[r["subject"]]["partial"] += r["partial"]
        by_subject[r["subject"]]["wrong"] += r["wrong"]
        by_subject[r["subject"]]["missing_rating"] += r["missing_rating"]
        by_subject[r["subject"]]["added_missing"] += r["added_missing"]
    print(f"{'subject':10}{'n':>6}{'C':>6}{'P':>6}{'W':>6}{'M':>6}{'prec':>8}{'rec':>8}")
    for subj, c in sorted(by_subject.items()):
        num = c["correct"] + 0.5 * c["partial"]
        prec = num / c["total"] if c["total"] else float("nan")
        rec = num / (c["total"] + c["added_missing"]) if c["total"] else float("nan")
        print(
            f"{subj:10}{c['total']:>6}{c['correct']:>6}{c['partial']:>6}"
            f"{c['wrong']:>6}{c['missing_rating']:>6}{prec:>8.3f}{rec:>8.3f}"
        )

    return 0


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_INPUT_DIR
    sys.exit(main(target))
