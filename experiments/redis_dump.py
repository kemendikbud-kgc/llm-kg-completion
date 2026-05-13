"""Read-only dump of every relevant Redis key (kg:courses + reviewer keys) to local JSON.

Pulls the source-of-truth triple datasets and every substantive reviewer's full
ratings/comments/missingTriples payload, writing them under
`data/expert_feedback/redis_snapshot_<date>/` so the rest of the analysis can be
done offline without re-hitting Redis.

USAGE: uv run --with redis --with certifi python experiments/redis_dump.py
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import certifi
import redis

REDIS_URL = (
    "rediss://default:gQAAAAAAAWfLAAIncDEyZjAzMWVmMDQ1OGM0ODk5YWFhZDAxY2IzOGVhNDY1MnAxOTIxMDc"
    "@communal-horse-92107.upstash.io:6379"
)

# Reviewers worth pulling: substantive (>=10 ratings) and not dummy
SUBSTANTIVE_MIN = 10
EXCLUDE_REVIEWERS = {"dummy-user-1", "admin"}


def main() -> int:
    r = redis.from_url(REDIS_URL, ssl_ca_certs=certifi.where(), decode_responses=True)
    print(f"PING={r.ping()}  DBSIZE={r.dbsize()}")

    out_dir = (
        Path("data/expert_feedback") / f"redis_snapshot_{date.today().isoformat()}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    courses_dir = out_dir / "courses"
    reviewers_dir = out_dir / "reviewers"
    courses_dir.mkdir(exist_ok=True)
    reviewers_dir.mkdir(exist_ok=True)

    # 1. kg:courses — the source-of-truth triple sets (one per course)
    courses_keys = sorted(r.keys("kg:courses*"))
    print(f"\nCourses keys: {courses_keys}")
    for k in courses_keys:
        raw = r.get(k)
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = raw  # fall back to raw string
        fname = k.replace(":", "__") + ".json"
        (courses_dir / fname).write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        size_kb = len(raw) / 1024
        print(f"   {k}  ({size_kb:.1f} KB)  -> courses/{fname}")

    # 2. Reviewer progress keys
    progress_keys = sorted(r.keys("kg:progress:*"))
    print(f"\nReviewer keys total: {len(progress_keys)}")
    kept = []
    for k in progress_keys:
        raw = r.get(k)
        if not raw:
            continue
        try:
            d = json.loads(raw)
        except Exception:
            continue

        rest = k.replace("kg:progress:", "")
        if ":" not in rest:
            continue
        reviewer, course = rest.split(":", 1)
        if reviewer in EXCLUDE_REVIEWERS:
            continue
        if len(d.get("ratings", {}) or {}) < SUBSTANTIVE_MIN:
            continue

        fname = f"{reviewer}__{course}.json"
        (reviewers_dir / fname).write_text(
            json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        kept.append((reviewer, course, len(d.get("ratings", {}))))

    print(f"\nKept {len(kept)} substantive reviewer payloads (>= {SUBSTANTIVE_MIN} ratings):")
    for reviewer, course, n in kept:
        print(f"   {reviewer:25}  {course:35}  n={n}")

    manifest = {
        "captured_at": date.today().isoformat(),
        "redis_url_host": "communal-horse-92107.upstash.io:6379",
        "courses_keys": courses_keys,
        "substantive_reviewers": [
            {"reviewer": rv, "course": co, "n_ratings": n} for rv, co, n in kept
        ],
        "excluded": sorted(EXCLUDE_REVIEWERS),
        "substantive_min_ratings": SUBSTANTIVE_MIN,
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nWrote snapshot manifest -> {out_dir / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
