"""Build the expert-review survey worksheet for the cross-book (LINTAS_BUKU) completion edges.

Source: ann-classifier-v1-KG-TEGAR-FIXED/lintas_buku_edges.t070_k20.json (the live yhoga set).
Output (data/completion_survey/):
  - lintas_buku_survey.csv   : one row per edge, score-BLIND, randomized, rubric columns blank
  - lintas_buku_survey.md    : readable brief for the team (per subject-pair) + instructions
  - low_confidence_excluded.csv : the <0.5 edges held out of the main survey

Design (per the agreed rubric):
  - Hide confidence/method (blinding) so experts aren't anchored.
  - Show proposed relation_type + description (that's what they're validating).
  - Randomized order (fixed seed) so relation-type/quality doesn't cluster.
  - Per-axis judgment: link valid? / relation type correct? / direction correct? + comment.
"""
import csv
import json
import random
from pathlib import Path

SRC = Path("experiments/knowledge_graph_states/completion-experiments/"
           "ann-classifier-v1-KG-TEGAR-FIXED/lintas_buku_edges.t070_k20.json")
OUT = Path("data/completion_survey")
CONF_CUTOFF = 0.5
SEED = 20260601  # fixed for reproducibility

REL_LABELS = {
    "LINTAS_BUKU_SAMA_DENGAN": "SAMA_DENGAN (konsep yang sama di buku berbeda)",
    "LINTAS_BUKU_PRASYARAT_UNTUK": "PRASYARAT_UNTUK (A prasyarat memahami B)",
    "LINTAS_BUKU_APLIKASI_DARI": "APLIKASI_DARI (A penerapan konsep B di disiplin lain)",
    "LINTAS_BUKU_MEMPERDALAM": "MEMPERDALAM (A memperdalam pemahaman B)",
    "LINTAS_BUKU_BERKAITAN_DENGAN": "BERKAITAN_DENGAN (berkaitan umum)",
}
short = lambda g: g.replace(" Kelas XII", "")


def load_edges():
    d = json.loads(SRC.read_text(encoding="utf-8"))
    rows = d if isinstance(d, list) else next(v for v in d.values() if isinstance(v, list))
    out = []
    for r in rows:
        p = r["properties"]
        out.append({
            "src": r["source_name"], "src_grade": r["source_grade"],
            "tgt": r["target_name"], "tgt_grade": r["target_grade"],
            "rel": r["rel_type"].replace("LINTAS_BUKU_", ""),
            "rel_full": r["rel_type"],
            "desc": p.get("description", ""),
            "conf": p.get("confidence"),
            "pair": " <-> ".join(sorted([short(r["source_grade"]), short(r["target_grade"])])),
        })
    return out


CSV_HEADER = [
    "id", "pasangan_mapel", "konsep_A", "mapel_A", "relasi_diusulkan",
    "konsep_B", "mapel_B", "penjelasan_LLM",
    # expert fills these:
    "1_relasi_valid? (Ya/Tidak)",
    "2_tipe_relasi_benar? (Benar/Salah)",
    "2b_jika_salah_tipe_yg_benar",
    "3_arah_benar? (Benar/Terbalik/NA)",
    "komentar",
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    edges = load_edges()
    main_edges = [e for e in edges if (e["conf"] or 0) >= CONF_CUTOFF]
    low = [e for e in edges if (e["conf"] or 0) < CONF_CUTOFF]

    rng = random.Random(SEED)
    rng.shuffle(main_edges)  # blind/randomize
    for i, e in enumerate(main_edges, 1):
        e["id"] = f"LB{i:03d}"

    # main survey CSV (score-blind: no conf/method columns)
    with (OUT / "lintas_buku_survey.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(CSV_HEADER)
        for e in main_edges:
            w.writerow([e["id"], e["pair"], e["src"], short(e["src_grade"]),
                        e["rel"], e["tgt"], short(e["tgt_grade"]), e["desc"],
                        "", "", "", "", ""])

    # held-out low-confidence CSV (kept for transparency, not in main survey)
    with (OUT / "low_confidence_excluded.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["konsep_A", "mapel_A", "relasi", "konsep_B", "mapel_B", "confidence", "penjelasan_LLM"])
        for e in sorted(low, key=lambda x: x["conf"]):
            w.writerow([e["src"], short(e["src_grade"]), e["rel"], e["tgt"],
                        short(e["tgt_grade"]), e["conf"], e["desc"]])

    # team brief (markdown)
    from collections import Counter
    by_pair = Counter(e["pair"] for e in main_edges)
    by_rel = Counter(e["rel"] for e in main_edges)
    md = []
    md.append("# Survei Validasi Relasi Lintas-Buku (Cross-Book Completion)\n")
    md.append(f"**{len(main_edges)} relasi** untuk divalidasi (confidence >= {CONF_CUTOFF}; "
              f"{len(low)} relasi confidence rendah dikeluarkan dari survei utama).\n")
    md.append("## Cara menilai setiap relasi\n")
    md.append("Untuk setiap baris **A —[RELASI]→ B**, nilai 3 aspek:\n")
    md.append("1. **Relasi valid?** — Apakah konsep A dan B benar-benar berkaitan? (Ya/Tidak)\n"
              "2. **Tipe relasi benar?** — Apakah label relasi yang diusulkan tepat? (Benar/Salah; jika salah, tulis tipe yang benar)\n"
              "3. **Arah benar?** — Apakah arah A→B sudah benar? (Benar/Terbalik/NA untuk relasi simetris)\n"
              "4. **Komentar** (opsional).\n")
    md.append("## Lima tipe relasi\n")
    for k, v in REL_LABELS.items():
        md.append(f"- **{v}**")
    md.append("")
    md.append("## Distribusi\n")
    md.append("| Pasangan Mapel | Jumlah |\n|---|--:|")
    for p, n in by_pair.most_common():
        md.append(f"| {p} | {n} |")
    md.append("\n| Tipe Relasi | Jumlah |\n|---|--:|")
    for rt, n in by_rel.most_common():
        md.append(f"| {rt} | {n} |")
    md.append("")
    md.append("## Daftar relasi (per pasangan mapel)\n")
    for pair in sorted(by_pair):
        md.append(f"### {pair}\n")
        md.append("| ID | Konsep A (mapel) | Relasi diusulkan | Konsep B (mapel) | Penjelasan |\n|---|---|---|---|---|")
        for e in [x for x in main_edges if x["pair"] == pair]:
            md.append(f"| {e['id']} | {e['src']} ({short(e['src_grade'])}) | "
                      f"**{e['rel']}** | {e['tgt']} ({short(e['tgt_grade'])}) | {e['desc']} |")
        md.append("")
    (OUT / "lintas_buku_survey.md").write_text("\n".join(md), encoding="utf-8")

    print(f"main survey edges: {len(main_edges)} | low-conf excluded: {len(low)}")
    print("rel dist:", dict(by_rel))
    print("pair dist:", dict(by_pair))
    print("wrote:", OUT / "lintas_buku_survey.csv", "|", OUT / "lintas_buku_survey.md",
          "|", OUT / "low_confidence_excluded.csv")


if __name__ == "__main__":
    main()
