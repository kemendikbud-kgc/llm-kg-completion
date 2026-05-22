"""Read-only inspection of Upstash Redis (kg-review-app backend)."""
from __future__ import annotations

import json
import os
import sys
from collections import Counter

import redis
import certifi

REDIS_URL = (
    "rediss://default:gQAAAAAAAWfLAAIncDEyZjAzMWVmMDQ1OGM0ODk5YWFhZDAxY2IzOGVhNDY1MnAxOTIxMDc"
    "@communal-horse-92107.upstash.io:6379"
)


def main() -> int:
    r = redis.from_url(REDIS_URL, ssl_ca_certs=certifi.where(), decode_responses=True)
    print(f"PING={r.ping()}  DBSIZE={r.dbsize()}")
    keys = sorted(r.keys("kg:progress:*"))
    rows = []
    for k in keys:
        raw = r.get(k)
        if not raw:
            continue
        try:
            d = json.loads(raw)
        except Exception as e:
            print(f"[parse-error] {k}: {e}")
            continue
        rest = k.replace("kg:progress:", "")
        # rest may be reviewer:course; reviewer is the first colon segment
        # but our reviewers contain hyphens, courses contain hyphens too — split on first ':'
        if ":" not in rest:
            continue
        reviewer, course = rest.split(":", 1)
        ratings = d.get("ratings", {}) or {}
        counts = Counter(ratings.values())
        miss = len(d.get("missingTriples", []) or [])
        comments = d.get("comments", {}) or {}
        completed = d.get("completedAt") or "-"
        updated = d.get("updatedAt") or "-"
        rows.append({
            "reviewer": reviewer,
            "course": course,
            "n": len(ratings),
            "C": counts.get("correct", 0),
            "P": counts.get("partial", 0),
            "W": counts.get("wrong", 0),
            "M": counts.get("missing", 0),
            "miss": miss,
            "comments": len(comments),
            "completed": completed,
            "updated": updated,
        })

    # filter to substantive
    substantive = [row for row in rows if row["n"] > 0]
    empty = [row for row in rows if row["n"] == 0]

    print(f"\nSubstantive entries: {len(substantive)}   Empty starters: {len(empty)}")
    print()
    hdr = (
        f"{'reviewer':30} {'course':35} {'n':>4} {'C':>4} {'P':>4} {'W':>4} {'M':>4} "
        f"{'+miss':>6} {'#cmt':>5} {'completed':21}"
    )
    print(hdr)
    print("-" * len(hdr))
    for row in substantive:
        prec = (row["C"] + 0.5 * row["P"]) / row["n"] if row["n"] else 0
        print(
            f"{row['reviewer']:30} {row['course']:35} "
            f"{row['n']:>4} {row['C']:>4} {row['P']:>4} {row['W']:>4} {row['M']:>4} "
            f"{row['miss']:>6} {row['comments']:>5} {row['completed'][:19]:21}  "
            f"prec={prec:.3f}"
        )

    print(f"\nEmpty starters ({len(empty)}):")
    for row in empty:
        print(f"  - {row['reviewer']} on {row['course']}  (updated {row['updated'][:19]})")

    # Look at exported folder vs DB to find new/missing
    exported_dir = r"C:\Users\Soros\Downloads\Feedback-20260506T040248Z-3-001\Feedback"
    if os.path.isdir(exported_dir):
        exported_reviewers = set()
        for fname in os.listdir(exported_dir):
            if fname.startswith("expert-") and fname.endswith(".json"):
                exported_reviewers.add(fname[:-5])  # strip .json
        in_db = {row["reviewer"] for row in substantive}
        print(f"\nExported on disk : {sorted(exported_reviewers)}")
        print(f"Substantive in DB: {sorted(in_db)}")
        print(f"In DB but NOT exported: {sorted(in_db - exported_reviewers)}")
        print(f"Exported but not in DB substantive: {sorted(exported_reviewers - in_db)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
