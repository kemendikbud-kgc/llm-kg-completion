"""Reusable client for the kg-review-app Upstash Redis backend.

Centralizes connection, key conventions, and read/write helpers so we stop
copy-pasting throwaway scripts. Read methods are safe; write methods are
explicit (save_progress / upsert_course / delete_progress).

Connection: set KG_REVIEW_REDIS_URL in the environment (preferred). Falls back
to the known project URL if unset, so existing workflows keep working.

Key conventions (kg-review-app):
    kg:courses                         -> JSON array of course records
    kg:progress:{reviewer}:{course}    -> JSON review-progress payload

Deps: redis, certifi  (uv run --with redis --with certifi ...)

CLI:
    python -m src.kg_review_redis summary
    python -m src.kg_review_redis dump [--out DIR]
    python -m src.kg_review_redis courses
    python -m src.kg_review_redis get <reviewer> <course>
"""
from __future__ import annotations

import json
import os
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Iterator

_DEFAULT_URL = (
    "rediss://default:gQAAAAAAAWfLAAIncDEyZjAzMWVmMDQ1OGM0ODk5YWFhZDAxY2IzOGVhNDY1MnAxOTIxMDc"
    "@communal-horse-92107.upstash.io:6379"
)

COURSES_KEY = "kg:courses"
PROGRESS_PREFIX = "kg:progress:"
RATING_LABELS = ("correct", "partial", "wrong", "missing")


def get_redis_url() -> str:
    """Resolve the Redis URL from env (KG_REVIEW_REDIS_URL) or the project default.

    Loads a local .env if python-dotenv is available, so KG_REVIEW_REDIS_URL set
    there is honored without manual exporting.
    """
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ModuleNotFoundError:
        pass
    return os.getenv("KG_REVIEW_REDIS_URL", _DEFAULT_URL)


class KGReviewRedis:
    """Thin, reusable wrapper over the kg-review-app Redis store.

    Example:
        kg = KGReviewRedis()
        for course in kg.list_courses():
            print(course["id"])
        prog = kg.get_progress("expert-biologi-4", "biologi-kelas-xii-1775626587840")
    """

    def __init__(self, url: str | None = None):
        self.url = url or get_redis_url()
        self._client = None  # lazy

    # ── connection ─────────────────────────────────────────────────
    @property
    def client(self):
        if self._client is None:
            import certifi
            import redis

            self._client = redis.from_url(
                self.url, ssl_ca_certs=certifi.where(), decode_responses=True
            )
        return self._client

    def ping(self) -> bool:
        return bool(self.client.ping())

    def dbsize(self) -> int:
        return int(self.client.dbsize())

    @staticmethod
    def _loads(raw):
        if not raw:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return raw

    # ── courses (read) ─────────────────────────────────────────────
    def list_courses(self) -> list[dict]:
        data = self._loads(self.client.get(COURSES_KEY))
        return data if isinstance(data, list) else []

    def get_course(self, course_id: str) -> dict | None:
        for c in self.list_courses():
            if c.get("id") == course_id:
                return c
        return None

    # ── progress (read) ────────────────────────────────────────────
    def progress_keys(self) -> list[str]:
        return sorted(self.client.keys(f"{PROGRESS_PREFIX}*"))

    @staticmethod
    def split_progress_key(key: str) -> tuple[str, str] | None:
        rest = key.replace(PROGRESS_PREFIX, "")
        if ":" not in rest:
            return None
        reviewer, course = rest.split(":", 1)  # reviewers/courses may contain hyphens
        return reviewer, course

    def get_progress(self, reviewer: str, course: str) -> dict | None:
        return self._loads(self.client.get(f"{PROGRESS_PREFIX}{reviewer}:{course}"))

    def iter_progress(self) -> Iterator[tuple[str, str, dict]]:
        for k in self.progress_keys():
            parsed = self.split_progress_key(k)
            payload = self._loads(self.client.get(k))
            if not parsed or not isinstance(payload, dict):
                continue
            reviewer, course = parsed
            yield reviewer, course, payload

    # ── writes (explicit) ──────────────────────────────────────────
    def save_progress(self, reviewer: str, course: str, payload: dict) -> None:
        """Overwrite a reviewer's progress payload for a course."""
        self.client.set(f"{PROGRESS_PREFIX}{reviewer}:{course}",
                        json.dumps(payload, ensure_ascii=False))

    def delete_progress(self, reviewer: str, course: str) -> int:
        return int(self.client.delete(f"{PROGRESS_PREFIX}{reviewer}:{course}"))

    def upsert_course(self, course: dict) -> None:
        """Insert/replace a course record in the kg:courses array (by id)."""
        cid = course.get("id")
        if not cid:
            raise ValueError("course must have an 'id'")
        courses = [c for c in self.list_courses() if c.get("id") != cid]
        courses.insert(0, course)
        self.client.set(COURSES_KEY, json.dumps(courses, ensure_ascii=False))

    # ── analysis helpers ───────────────────────────────────────────
    def summary_rows(self, exclude: set[str] | None = None, min_ratings: int = 1) -> list[dict]:
        """Per-reviewer rating summary (the redis_check view)."""
        exclude = exclude or set()
        rows = []
        for reviewer, course, d in self.iter_progress():
            if reviewer in exclude:
                continue
            ratings = d.get("ratings", {}) or {}
            if len(ratings) < min_ratings:
                continue
            c = Counter(ratings.values())
            n = len(ratings)
            graded = c.get("correct", 0) + 0.5 * c.get("partial", 0)
            rows.append({
                "reviewer": reviewer, "course": course, "n": n,
                **{lab[0].upper(): c.get(lab, 0) for lab in RATING_LABELS},
                "missing_triples": len(d.get("missingTriples", []) or []),
                "comments": len(d.get("comments", {}) or {}),
                "completed": d.get("completedAt") or "-",
                "updated": d.get("updatedAt") or "-",
                "precision": round(graded / n, 3) if n else 0.0,
            })
        return sorted(rows, key=lambda r: (r["reviewer"], r["course"]))

    def dump_snapshot(self, out_dir: Path | None = None,
                      exclude: set[str] | None = None, min_ratings: int = 10) -> Path:
        """Mirror kg:courses + substantive reviewer payloads to local JSON."""
        exclude = exclude or {"dummy-user-1", "admin"}
        out_dir = out_dir or (Path("data/expert_feedback") / f"redis_snapshot_{date.today().isoformat()}")
        (out_dir / "courses").mkdir(parents=True, exist_ok=True)
        (out_dir / "reviewers").mkdir(parents=True, exist_ok=True)

        for k in sorted(self.client.keys("kg:courses*")):
            data = self._loads(self.client.get(k))
            (out_dir / "courses" / (k.replace(":", "__") + ".json")).write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

        kept = []
        for reviewer, course, d in self.iter_progress():
            if reviewer in exclude or len(d.get("ratings", {}) or {}) < min_ratings:
                continue
            (out_dir / "reviewers" / f"{reviewer}__{course}.json").write_text(
                json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
            kept.append({"reviewer": reviewer, "course": course, "n_ratings": len(d["ratings"])})

        (out_dir / "manifest.json").write_text(json.dumps({
            "captured_at": date.today().isoformat(),
            "substantive_reviewers": kept,
            "excluded": sorted(exclude),
            "substantive_min_ratings": min_ratings,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        return out_dir


# ── CLI ────────────────────────────────────────────────────────────
def _main(argv: list[str] | None = None) -> int:
    import argparse

    p = argparse.ArgumentParser(description="kg-review-app Redis client")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("summary", help="per-reviewer rating summary")
    d = sub.add_parser("dump", help="mirror courses + reviewers to local JSON")
    d.add_argument("--out", default=None)
    sub.add_parser("courses", help="list course ids")
    g = sub.add_parser("get", help="print one reviewer's progress")
    g.add_argument("reviewer"); g.add_argument("course")
    args = p.parse_args(argv)

    kg = KGReviewRedis()
    print(f"PING={kg.ping()}  DBSIZE={kg.dbsize()}  URL={kg.url.split('@')[-1]}")

    if args.cmd == "summary":
        rows = kg.summary_rows()
        print(f"\n{len(rows)} substantive entries\n")
        hdr = f"{'reviewer':30}{'course':38}{'n':>4}{'C':>4}{'P':>4}{'W':>4}{'M':>4}{'prec':>7}"
        print(hdr); print("-" * len(hdr))
        for r in rows:
            print(f"{r['reviewer']:30}{r['course']:38}{r['n']:>4}{r['C']:>4}{r['P']:>4}"
                  f"{r['W']:>4}{r['M']:>4}{r['precision']:>7}")
    elif args.cmd == "dump":
        out = kg.dump_snapshot(Path(args.out) if args.out else None)
        print(f"snapshot -> {out}")
    elif args.cmd == "courses":
        for c in kg.list_courses():
            print(f"  {c.get('id')}  ({c.get('grade','?')})  triples~{len(c.get('chapters') or [])}ch")
    elif args.cmd == "get":
        prog = kg.get_progress(args.reviewer, args.course)
        print(json.dumps(prog, ensure_ascii=False, indent=2) if prog else "(not found)")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
