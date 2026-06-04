"""Re-qualify cross-book completion edges across the threshold/top_k sweep
WITHOUT any API key, using the on-disk embedding cache.

Why this exists
---------------
The completion ANN-retrieval scores (cosine) and top_k ranks are NOT persisted
in lintas_buku_edges.t070_k20.json (only description/confidence survive). The
yhoga Neo4j graph already holds the 125 LINTAS_BUKU edges, so re-running the
Streamlit completion page finds 0 new pairs (skip_existing_typed_edges). And
the embedding API key has been deleted.

But the embedding vectors are cached on disk (data/embedding_cache/, keyed by
sha256(embed_text + model)). Cosine similarity is just the normalized dot
product of those vectors, and top_k rank is recoverable by ranking each node's
neighbors. So we can recompute, for every surveyed edge, its cosine + rank, and
decide which sweep configs (threshold, top_k) it survives — then join the pilot
expert ratings to report per-config quality. Zero API calls, no graph mutation.

Retrieval semantics replicated from src/completion.find_similar_pairs_ann:
  - query_similar_nodes returns the top_k nearest neighbors over the WHOLE index
    (any grade) with score >= threshold; the cross-grade filter is applied AFTER.
  - Every node queries; a pair (a,b) is kept if EITHER direction retrieves the
    other, deduped by sorted name. So a cross-grade pair survives config (t,k)
    iff  cos(a,b) >= t  AND  min(rank_a(b), rank_b(a)) <= k,
    where rank_a(b) ranks b among ALL of a's neighbors by descending cosine.

Usage:
  uv run --with neo4j --with python-dotenv --with numpy \
      python experiments/scripts/requalify_completion_from_cache.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.config import DEFAULT_EMBEDDING_MODEL  # noqa: E402
from src.schema_adapter import YhogaAdapter  # noqa: E402

EMBED_CACHE = ROOT / "data" / "embedding_cache"
SURVEY_CSV = ROOT / "data" / "completion_survey" / "lintas_buku_survey.csv"
RESPONSES_CSV = ROOT / "data" / "completion_survey" / "lintas_buku_survey_responses.csv"
OUT_CSV = ROOT / "data" / "completion_survey" / "sweep_requalification.csv"
OUT_MD = ROOT / "data" / "completion_survey" / "sweep_requalification.md"

# Sweep grid: (threshold, top_k). Threshold rises as top_k falls (coupled).
SWEEP = [(0.85, 5), (0.80, 10), (0.75, 15), (0.70, 20)]

VALID_COL = "1_relasi_valid? (Ya/Tidak)"
TYPE_COL = "2_tipe_relasi_benar? (Benar/Salah)"
DIR_COL = "3_arah_benar? (Benar/Terbalik/NA)"


def embed_key(text: str, model: str) -> str:
    return hashlib.sha256((text + model).encode()).hexdigest()


def load_cached_vectors(nodes: list[dict], adapter, model: str):
    """Return (name->unit_vector dict, list of names missing from cache)."""
    vecs: dict[str, np.ndarray] = {}
    missing: list[str] = []
    for n in nodes:
        text = adapter.build_embed_text(n)
        f = EMBED_CACHE / f"{embed_key(text, model)}.json"
        if not f.exists():
            missing.append(n["name"])
            continue
        v = np.asarray(json.loads(f.read_text())["embedding"], dtype=np.float64)
        nrm = np.linalg.norm(v)
        if nrm == 0:
            missing.append(n["name"])
            continue
        vecs[n["name"]] = v / nrm
    return vecs, missing


def main() -> int:
    from dotenv import load_dotenv
    from neo4j import GraphDatabase

    load_dotenv()
    model = DEFAULT_EMBEDDING_MODEL
    adapter = YhogaAdapter()

    # 1. Pull concepts (name/description/materi_pokok_ref/grade) from yhoga.
    drv = GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"]),
    )
    with drv.session() as s:
        nodes = [
            dict(r)
            for r in s.run(
                "MATCH (c:Concept) RETURN c.name AS name, c.description AS description, "
                "c.materi_pokok_ref AS materi_pokok_ref, c.grade AS grade"
            )
        ]
    drv.close()

    grade_by_name = {n["name"]: (n.get("grade") or "") for n in nodes}
    vecs, missing = load_cached_vectors(nodes, adapter, model)
    print(f"concepts={len(nodes)}  cached_vectors={len(vecs)}  missing={len(missing)}")

    # 2. Cosine matrix over cached nodes (unit vectors -> dot = cosine).
    names = list(vecs.keys())
    idx = {nm: i for i, nm in enumerate(names)}
    M = np.vstack([vecs[nm] for nm in names])  # (N, 3072)
    cos = M @ M.T  # (N, N)
    np.fill_diagonal(cos, -np.inf)  # exclude self when ranking

    def rank_of(query: str, target: str) -> int | None:
        """1-based rank of `target` among `query`'s neighbors by desc cosine
        over ALL nodes (any grade), matching the whole-index top_k retrieval."""
        if query not in idx or target not in idx:
            return None
        qi, ti = idx[query], idx[target]
        c = cos[qi, ti]
        # rank = 1 + (# neighbors strictly more similar than target)
        return int(np.sum(cos[qi] > c)) + 1

    # 3. Load surveyed edges (LB id -> src/tgt names) + ratings.
    meta: dict[str, dict] = {}
    with open(SURVEY_CSV, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            meta[r["id"]] = r
    ratings: dict[str, dict] = {}
    with open(RESPONSES_CSV, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            ratings[r["id"]] = r

    # 4. Per-edge cosine/rank + survival per config.
    rows = []
    for lb, m in meta.items():
        a, b = m["konsep_A"], m["konsep_B"]
        computable = a in idx and b in idx
        c = float(cos[idx[a], idx[b]]) if computable else None
        ra = rank_of(a, b)
        rb = rank_of(b, a)
        best_rank = min([x for x in (ra, rb) if x is not None], default=None)
        row = {
            "id": lb,
            "konsep_A": a,
            "konsep_B": b,
            "pasangan_mapel": m.get("pasangan_mapel", ""),
            "relasi": m.get("relasi_diusulkan", ""),
            "cosine": round(c, 4) if c is not None else "",
            "rank_A->B": ra if ra is not None else "",
            "rank_B->A": rb if rb is not None else "",
            "best_rank": best_rank if best_rank is not None else "",
            "computable": computable,
        }
        # Neo4j vector index reports cosine as a normalized score (1+cos)/2 in
        # [0,1]; the threshold slider is applied to THAT score. So compare the
        # normalized score, not the raw cosine.
        score = (1.0 + c) / 2.0 if c is not None else None
        for t, k in SWEEP:
            survives = bool(
                computable and score is not None and score >= t
                and best_rank is not None and best_rank <= k
            )
            row[f"t{int(t*100)}_k{k}"] = survives
        # carry ratings
        rr = ratings.get(lb, {})
        row["valid"] = rr.get(VALID_COL, "")
        row["type_ok"] = rr.get(TYPE_COL, "")
        row["direction"] = rr.get(DIR_COL, "")
        rows.append(row)

    # 5. Write per-edge CSV.
    fieldnames = list(rows[0].keys())
    with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    # 6. Aggregate per config: survivors + survey-joined quality of survivors.
    def pct(num, den):
        return f"{num/den*100:.0f}%" if den else "—"

    agg = []
    for t, k in SWEEP:
        col = f"t{int(t*100)}_k{k}"
        surv = [r for r in rows if r[col]]
        rated = [r for r in surv if r["valid"] in ("Ya", "Tidak")]
        n = len(rated)
        valid_ok = sum(1 for r in rated if r["valid"] == "Ya")
        type_ok = sum(1 for r in rated if r["type_ok"] == "Benar")
        dir_rated = [r for r in rated if r["direction"] in ("Benar", "Terbalik")]
        dir_ok = sum(1 for r in dir_rated if r["direction"] == "Benar")
        agg.append({
            "config": f"{t:.2f} / k{k}",
            "survivors": len(surv),
            "rated": n,
            "validity": pct(valid_ok, n),
            "type": pct(type_ok, n),
            "direction": pct(dir_ok, len(dir_rated)),
        })

    # uncomputable surveyed edges (involve a non-cached node)
    uncomp = [r["id"] for r in rows if not r["computable"]]

    lines = []
    lines.append("# Sweep Re-Qualification (cache-based, no API key)\n")
    lines.append(
        f"Recomputed cosine + top_k rank for {len(rows)} surveyed cross-book edges "
        f"from {len(vecs)} cached embedding vectors (model `{model}`). "
        f"No API calls, no Neo4j mutation.\n"
    )
    lines.append("## Survivors and survey-joined quality per config\n")
    lines.append("| Config | Survivors | Rated | Validity | Type | Direction |")
    lines.append("|---|--:|--:|--:|--:|--:|")
    for a in agg:
        lines.append(
            f"| {a['config']} | {a['survivors']} | {a['rated']} | "
            f"{a['validity']} | {a['type']} | {a['direction']} |"
        )
    lines.append("")
    if uncomp:
        lines.append(
            f"> {len(uncomp)} surveyed edge(s) involve a concept missing from the "
            f"embedding cache (description changed since embedding) and are excluded "
            f"from survival: {', '.join(uncomp)}\n"
        )
    if missing:
        lines.append(
            f"> {len(missing)} of {len(nodes)} graph concepts lack a cached vector "
            f"(re-embed needed for a full run): {', '.join(missing[:12])}"
            + (" …" if len(missing) > 12 else "") + "\n"
        )
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")

    print("\n".join(lines))
    print(f"\nwrote {OUT_CSV}\nwrote {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
