"""Read-only dump of every relevant Redis key (kg:courses + reviewer keys) to local JSON.

Thin wrapper kept for backwards-compatible invocation. The reusable logic now
lives in src/kg_review_redis.py (KGReviewRedis.dump_snapshot).

USAGE: uv run --with redis --with certifi python experiments/scripts/redis_dump.py
   or: python -m src.kg_review_redis dump
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.kg_review_redis import _main

if __name__ == "__main__":
    sys.exit(_main(["dump"]))
