"""Assemble the paper's canonical dataset bundle into data/canonical/.

Collects ONE authoritative artifact per pipeline stage (Step 1 Extraction →
Consensus → Step 2 Completion → Final) out of the scattered repo locations,
and writes a README.md provenance manifest with real counts. Single source of
truth for what the paper actually used; ready to upload to the Drive folder.

Canonical choices (per project decisions):
  - Extraction : final-kg/extracted/*.json
  - Consensus  : final-kg/final-consensus/kg_repaired/*.consensus.repaired.json
  - Completion : ann-classifier-v1-KG-TEGAR-FIXED/lintas_buku_edges.t070_k20.json (0.70/k20, 125 edges)
  - Final      : provided/uploaded separately by the author (placeholder note here)

Usage:  uv run python experiments/scripts/build_canonical_bundle.py
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "canonical"

SUBJECTS = ["Biologi Kelas XII", "Fisika Kelas XII", "Kimia Kelas XII"]

EXTRACT = ROOT / "final-kg" / "extracted"
CONSENSUS = ROOT / "final-kg" / "final-consensus"
COMPLETION = (ROOT / "experiments" / "knowledge_graph_states" / "completion-experiments"
              / "ann-classifier-v1-KG-TEGAR-FIXED" / "lintas_buku_edges.t070_k20.json")
SURVEY = ROOT / "data" / "completion_survey"


def copy(src: Path, dstdir: Path) -> str:
    dstdir.mkdir(parents=True, exist_ok=True)
    if not src.exists():
        return f"  ⚠ MISSING: {src.relative_to(ROOT)}"
    shutil.copy2(src, dstdir / src.name)
    return f"  ✓ {src.name}"


def count_concepts(path: Path) -> int:
    """Best-effort concept count by walking the extracted JSON."""
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return -1
    n = 0
    def walk(o):
        nonlocal n
        if isinstance(o, dict):
            if "concepts" in o and isinstance(o["concepts"], list):
                n += len(o["concepts"])
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(d)
    return n


def main() -> int:
    log: list[str] = []

    # 01 — Extraction
    d = OUT / "01_extraction"
    log.append("01_extraction/")
    for s in SUBJECTS:
        log.append(copy(EXTRACT / f"{s}.json", d))
    for extra in ("manifest.json", "dropped_triples.json"):
        log.append(copy(EXTRACT / extra, d))

    # 02 — Consensus (repaired = canonical)
    d = OUT / "02_consensus"
    log.append("02_consensus/")
    for s in SUBJECTS:
        log.append(copy(CONSENSUS / "kg_repaired" / f"{s}.consensus.repaired.json", d))
        log.append(copy(CONSENSUS / "kg_repaired" / f"{s}.report.json", d))
    for s in ("biologi", "fisika", "kimia"):
        log.append(copy(CONSENSUS / f"{s}_gold_standard.json", d))
    vdir = CONSENSUS / "validations"
    if vdir.exists():
        for f in sorted(vdir.glob("expert-*.json")):
            log.append(copy(f, d / "validations"))

    # 03 — Completion
    d = OUT / "03_completion"
    log.append("03_completion/")
    log.append(copy(COMPLETION, d))
    log.append(copy(SURVEY / "node_descriptions.md", d))
    log.append(copy(SURVEY / "lintas_buku_survey.csv", d))
    log.append(copy(SURVEY / "lintas_buku_survey_responses.csv", d))

    # 04 — Final (author uploads separately)
    d = OUT / "04_final"
    d.mkdir(parents=True, exist_ok=True)
    (d / "README.md").write_text(
        "# 04 — Final KG\n\n"
        "Artefak Final (KG gabungan: konsensus + 125 edge LINTAS_BUKU, sebagaimana "
        "termuat di yhoga Neo4j) **diunggah terpisah oleh penulis**.\n\n"
        "Isi yang diharapkan: ekspor node+edge dari yhoga Neo4j (JSON atau Cypher dump) "
        "+ ringkasan statistik graf (jumlah node per label, total relasi, 125 LINTAS_BUKU).\n",
        encoding="utf-8")
    log.append("04_final/  (placeholder — author uploads Final)")

    # ── counts for manifest ──
    concept_counts = {s: count_concepts(EXTRACT / f"{s}.json") for s in SUBJECTS}
    comp = json.loads(COMPLETION.read_text(encoding="utf-8")) if COMPLETION.exists() else {}
    edges = comp.get("edges", []) if isinstance(comp, dict) else comp
    from collections import Counter
    dist = Counter(e["rel_type"].replace("LINTAS_BUKU_", "") for e in edges) if edges else {}

    readme = OUT / "README.md"
    lines = [
        "# Paper Data (Canonical)\n",
        "Data kanonik yang digunakan paper, satu artefak otoritatif per tahap pipeline.\n",
        "## Tahapan\n",
        "| Tahap | Folder | Sumber | Model / Parameter | Jumlah |",
        "|---|---|---|---|---|",
        f"| Step 1 — Ekstraksi | `01_extraction/` | final-kg/extracted | Gemini 2.5 Flash Lite; chunk 800/200 | "
        f"konsep: " + ", ".join(f"{s.split()[0]} {concept_counts[s]}" for s in SUBJECTS) + " |",
        "| Konsensus | `02_consensus/` | final-kg/final-consensus/kg_repaired | multi-judge + repair (PR #1) | "
        "3 mapel (repaired) + gold standards + 6 validasi pakar |",
        f"| Step 2 — Completion | `03_completion/` | ann-classifier-v1-KG-TEGAR-FIXED | Gemini 2.5 Flash; embed gemini-embedding-001; threshold 0,70 / top_k 20 | "
        f"{len(edges)} edge (" + ", ".join(f"{k} {v}" for k, v in dist.most_common()) + ") |",
        "| Final | `04_final/` | yhoga Neo4j (diunggah penulis) | konsensus + 125 LINTAS_BUKU | lihat 04_final/README.md |",
        "",
        "## Catatan provenans",
        "- Konsensus kanonik = varian **repaired** (kg_repaired), bukan (2.5-pro) / (mock).",
        "- Completion config final = **0,70 / k20** (125 edge); 8 edge confidence < 0,5 dikeluarkan dari survei (117 dinilai).",
        "- Validasi pakar lintas-buku (Fase 2): pilot 1 penilai, 100/117 (validitas 99% / tipe 98% / arah 74%).",
        "- Versi lain (extraction-v1..v4, consensus 2.5-pro/mock) BUKAN kanonik — diarsipkan terpisah.",
        "",
    ]
    readme.write_text("\n".join(lines), encoding="utf-8")

    print("\n".join(log))
    print(f"\nManifest: {readme}")
    print(f"Bundle root: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
