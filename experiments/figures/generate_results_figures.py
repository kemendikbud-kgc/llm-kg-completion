"""Generate 5 results figures for Bab 4 Dev.

Reads data from existing audit artifacts:
  - experiments/yhoga-boosted-peer/{subj}_base.json  (3 books)
  - experiments/yhoga-ann-v1/lintas_buku_edges.t075_k15.json
  - experiments/yhoga-ann-v1/lintas_buku_edges.t085_k5.json (iter 1, optional)

Outputs PNGs to experiments/figures/. Re-runnable; idempotent.

Run:
    python experiments/figures/generate_results_figures.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib

# --- Paths --------------------------------------------------------------
HERE  = Path(__file__).parent
ROOT  = HERE.parent
PEER  = ROOT / "yhoga-boosted-peer"
ANNV1 = ROOT / "yhoga-ann-v1"

# --- Style --------------------------------------------------------------
plt.rcParams.update({
    "font.family":           "DejaVu Sans",
    "font.size":             11,
    "axes.titlesize":        12,
    "axes.labelsize":        11,
    "axes.titleweight":      "bold",
    "axes.spines.top":       False,
    "axes.spines.right":     False,
    "figure.dpi":            150,
    "savefig.dpi":           200,
    "savefig.bbox":          "tight",
    "savefig.facecolor":     "white",
})

# Subject palette — used consistently across all figures
COLOR = {
    "Biologi": "#3da35d",
    "Fisika":  "#5b8def",
    "Kimia":   "#ee6c4d",
}
ANN_COLOR = "#1565c0"   # ann-v1
NEW_COLOR = "#d84315"   # new (peer notebook)


def _load_books() -> dict[str, dict]:
    return {
        "Biologi": json.load(open(PEER / "biologi_base.json", encoding="utf-8")),
        "Fisika":  json.load(open(PEER / "fisika_base.json",  encoding="utf-8")),
        "Kimia":   json.load(open(PEER / "kimia_base.json",   encoding="utf-8")),
    }


def _load_ann_v1() -> list[dict]:
    p = ANNV1 / "lintas_buku_edges.t075_k15.json"
    return json.load(open(p, encoding="utf-8"))["edges"]


# =========================================================================
# Figure 1 — Orphan rate per book
# =========================================================================
def fig_orphan_rates(out: Path) -> None:
    books = _load_books()
    rows = []
    for subj, d in books.items():
        total, orphans = 0, 0
        for ch in d["chapters"]:
            for st in ch.get("subtopics", []):
                for c in st.get("concepts", []):
                    total += 1
                    if not c.get("relations") and not c.get("cross_book_links"):
                        orphans += 1
        rows.append((subj, total, orphans, 100 * orphans / max(total, 1)))

    fig, ax = plt.subplots(figsize=(7.5, 3.5))
    subjs = [r[0] for r in rows]
    pcts  = [r[3] for r in rows]
    ns    = [(r[2], r[1]) for r in rows]
    colors = [COLOR[s] for s in subjs]
    bars = ax.barh(subjs, pcts, color=colors, edgecolor="white", height=0.6)
    for bar, (orph, tot), pct in zip(bars, ns, pcts):
        ax.text(pct + 1.5, bar.get_y() + bar.get_height() / 2,
                f"{pct:.0f}%  ({orph}/{tot})",
                va="center", fontsize=10, color="#333")
    ax.set_xlim(0, max(pcts) * 1.35)
    ax.set_xlabel("Persentase konsep tanpa relasi (intra-book maupun cross-book)")
    ax.set_title("Konsep orphan per mata pelajaran  —  Tahap 2 ekstraksi base")
    ax.invert_yaxis()
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(decimals=0))
    ax.grid(axis="x", alpha=0.3)
    plt.savefig(out / "fig_orphan_rates.png")
    plt.close(fig)
    return rows


# =========================================================================
# Figure 2 — Intra-book relation type distribution (long-tail)
# =========================================================================
def fig_type_distribution(out: Path) -> None:
    books = _load_books()
    TOP_N = 12
    fig, axes = plt.subplots(1, 3, figsize=(14, 5.0))  # no sharey: each panel sizes own labels
    for ax, (subj, d) in zip(axes, books.items()):
        types = Counter()
        for ch in d["chapters"]:
            for st in ch.get("subtopics", []):
                for c in st.get("concepts", []):
                    for r in c.get("relations", []):
                        types[r.get("type", "?")] += 1
        ranked  = types.most_common()
        n_types = len(types)
        n_edges = sum(c for _, c in ranked)
        # Cap to top-N; bucket the rest under "+(N) lainnya"
        head = ranked[:TOP_N]
        tail = ranked[TOP_N:]
        names  = [t for t, _ in head]
        counts = [n for _, n in head]
        if tail:
            tail_count = sum(n for _, n in tail)
            names.append(f"… +{len(tail)} tipe lain")
            counts.append(tail_count)

        bars = ax.barh(range(len(names)), counts, color=COLOR[subj],
                       edgecolor="white", height=0.72)
        # Grey-out the "+N lainnya" bucket for visual distinction
        if tail:
            bars[-1].set_color("#bdbdbd")
        for bar, c in zip(bars, counts):
            ax.text(c + 0.4, bar.get_y() + bar.get_height()/2,
                    str(c), va="center", fontsize=9, color="#333")
        ax.set_yticks(range(len(names)))
        ax.set_yticklabels(names, fontsize=10)
        ax.invert_yaxis()
        ax.set_title(f"{subj}  —  {n_types} tipe / {n_edges} edge", fontsize=12)
        ax.set_xlabel("Jumlah edge")
        ax.set_xlim(0, max(counts) * 1.18)
        ax.grid(axis="x", alpha=0.3)
        ax.text(0.98, 0.02,
                f"top-3 = {sum(c for _, c in ranked[:3])}/{n_edges} "
                f"({100*sum(c for _, c in ranked[:3])/n_edges:.0f}%)",
                transform=ax.transAxes, ha="right", fontsize=9, color="#555",
                bbox=dict(facecolor="white", edgecolor="none", alpha=0.85))
    fig.suptitle("Distribusi tipe relasi intra-buku  —  open-vocab problem",
                 fontsize=13, fontweight="bold", y=1.00)
    fig.tight_layout()
    plt.savefig(out / "fig_type_distribution.png")
    plt.close(fig)


# =========================================================================
# Figure 3 — Cross-book type composition: ann-v1 vs new (peer)
# =========================================================================
def fig_crossbook_types(out: Path) -> None:
    ann = _load_ann_v1()
    ann_types = Counter(e["properties"]["relation_type"] for e in ann)
    # ann_types keys are stripped of LINTAS_BUKU_ prefix already

    # new (peer) cross-book links — sum across the 3 base books
    new_types = Counter()
    for fn in ("biologi_base.json", "fisika_base.json", "kimia_base.json"):
        d = json.load(open(PEER / fn, encoding="utf-8"))
        for ch in d["chapters"]:
            for st in ch.get("subtopics", []):
                for c in st.get("concepts", []):
                    for ln in c.get("cross_book_links", []) or []:
                        new_types[ln.get("relation_type", "?")] += 1

    canonical = ["PRASYARAT_UNTUK", "MEMPERDALAM", "APLIKASI_DARI",
                 "BERKAITAN_DENGAN", "SAMA_DENGAN"]
    leak_keys = sorted(k for k in new_types if k not in canonical)
    keys = canonical + leak_keys

    ann_vals = [ann_types.get(k, 0) for k in keys]
    new_vals = [new_types.get(k, 0) for k in keys]
    ann_tot, new_tot = sum(ann_types.values()), sum(new_types.values())

    fig, ax = plt.subplots(figsize=(10, 4.5))
    x = range(len(keys))
    width = 0.4
    b1 = ax.bar([i - width/2 for i in x], ann_vals, width,
                color=ANN_COLOR, label=f"ann-v1  (n={ann_tot})", edgecolor="white")
    b2 = ax.bar([i + width/2 for i in x], new_vals, width,
                color=NEW_COLOR, label=f"new (peer)  (n={new_tot})", edgecolor="white")
    for bar in list(b1) + list(b2):
        h = bar.get_height()
        if h > 0:
            ax.text(bar.get_x() + bar.get_width()/2, h + 0.8,
                    f"{int(h)}", ha="center", fontsize=9, color="#333")
    # Flag open-vocab leaks visually — band only; legend below carries the label
    for i, k in enumerate(keys):
        if k not in canonical:
            ax.axvspan(i - 0.5, i + 0.5, color="#fff3e0", alpha=0.7, zorder=0)

    ax.set_xticks(list(x))
    # Color the leak labels orange so the band has a referent
    xticklabels = []
    for k in keys:
        xticklabels.append(k)
    ax.set_xticklabels(xticklabels, rotation=15, ha="right", fontsize=10)
    for tick_label, k in zip(ax.get_xticklabels(), keys):
        if k not in canonical:
            tick_label.set_color("#bf5c00")
            tick_label.set_fontstyle("italic")

    ax.set_ylabel("Jumlah edge")
    ax.set_ylim(0, max(ann_vals + new_vals) * 1.20)
    ax.set_title("Komposisi tipe edge cross-book — ann-v1 vs new (peer)")
    # Legend in upper-left so it doesn't fight the tall BERKAITAN_DENGAN bar
    ax.legend(loc="upper left", frameon=False)
    # Explanatory note below x-axis instead of overlapping the bars
    fig.text(0.5, -0.04,
             "Tipe ber-warna oranye + background pastel = open-vocab leak "
             "(bukan dari closed set 5-tipe LINTAS_BUKU_*).",
             ha="center", fontsize=9, color="#bf5c00", style="italic")
    ax.grid(axis="y", alpha=0.3)
    plt.savefig(out / "fig_crossbook_types.png")
    plt.close(fig)


# =========================================================================
# Figure 4 — Subject-pair coverage (Bio↔Kim / Fis↔Kim / Bio↔Fis)
# =========================================================================
def fig_subject_pairs(out: Path) -> None:
    ann = _load_ann_v1()
    new_edges = []
    for fn in ("biologi_base.json", "fisika_base.json", "kimia_base.json"):
        d = json.load(open(PEER / fn, encoding="utf-8"))
        src_grade = d.get("grade")
        for ch in d["chapters"]:
            for st in ch.get("subtopics", []):
                for c in st.get("concepts", []):
                    for ln in c.get("cross_book_links", []) or []:
                        tgt = ln.get("target_book")
                        if tgt and src_grade:
                            new_edges.append((src_grade, tgt))

    def pair_label(a, b):
        # short subject name without "Kelas XII"
        short = lambda s: s.replace(" Kelas XII", "")
        return " <-> ".join(sorted([short(a), short(b)]))

    ann_pairs = Counter(pair_label(e["source_grade"], e["target_grade"]) for e in ann)
    new_pairs = Counter(pair_label(a, b) for (a, b) in new_edges)
    # Dedupe undirected pairs in new (peer stores each direction once per source book)
    # Already deduped by pair_label sort order, so the count above double-counts.
    # Halve the new counts for true undirected (peer stores each end).
    # Actually peer stores cross_book_links only on one end (source -> target), so do NOT halve.
    # ann edges in the JSON are undirected pairs already (one per pair).

    keys = ["Biologi <-> Kimia", "Fisika <-> Kimia", "Biologi <-> Fisika"]
    ann_vals = [ann_pairs.get(k, 0) for k in keys]
    new_vals = [new_pairs.get(k, 0) for k in keys]

    fig, ax = plt.subplots(figsize=(9, 4.5))
    x = range(len(keys))
    width = 0.4
    b1 = ax.bar([i - width/2 for i in x], ann_vals, width,
                color=ANN_COLOR, label=f"ann-v1  (n={sum(ann_vals)})", edgecolor="white")
    b2 = ax.bar([i + width/2 for i in x], new_vals, width,
                color=NEW_COLOR, label=f"new (peer)  (n={sum(new_vals)})", edgecolor="white")
    for bar, val, tot in zip(list(b1)+list(b2), ann_vals+new_vals,
                              [sum(ann_vals)]*len(keys)+[sum(new_vals)]*len(keys)):
        if val > 0:
            ax.text(bar.get_x()+bar.get_width()/2, val+0.8,
                    f"{val}  ({100*val/max(tot,1):.0f}%)",
                    ha="center", fontsize=9, color="#333")
    ax.set_xticks(list(x))
    ax.set_xticklabels(keys, fontsize=10)
    ax.set_ylabel("Jumlah edge cross-book")
    ax.set_ylim(0, max(ann_vals + new_vals) * 1.18)
    ax.set_title("Cakupan pasangan mata pelajaran — domain balance per metode")
    ax.legend(loc="center right", frameon=False)
    ax.grid(axis="y", alpha=0.3)
    plt.savefig(out / "fig_subject_pairs.png")
    plt.close(fig)


# =========================================================================
# Figure 5 — ann-v1 confidence distribution
# =========================================================================
def fig_confidence_distribution(out: Path) -> None:
    ann = _load_ann_v1()
    confs = [float(e["properties"]["confidence"]) for e in ann]
    buckets = [
        ("< 0.50",      lambda c: c < 0.50),
        ("0.50 - 0.70", lambda c: 0.50 <= c < 0.70),
        ("0.70 - 0.85", lambda c: 0.70 <= c < 0.85),
        ("0.85 - 0.95", lambda c: 0.85 <= c < 0.95),
        ("≥ 0.95",      lambda c: c >= 0.95),
    ]
    counts = [sum(1 for c in confs if pred(c)) for (_, pred) in buckets]
    pal = ["#c62828", "#ef6c00", "#f9a825", "#558b2f", "#1b5e20"]

    fig, ax = plt.subplots(figsize=(8, 3.8))
    labels = [b[0] for b in buckets]
    bars = ax.bar(labels, counts, color=pal, edgecolor="white")
    n = sum(counts)
    for bar, c in zip(bars, counts):
        if c > 0:
            ax.text(bar.get_x()+bar.get_width()/2, c+0.5,
                    f"{c}  ({100*c/max(n,1):.1f}%)",
                    ha="center", fontsize=9, color="#333")
    ax.set_ylabel("Jumlah edge")
    ax.set_title(f"Distribusi confidence — ann-v1 (n={n}, mean={sum(confs)/n:.2f})")
    ax.set_ylim(0, max(counts) * 1.32)
    ax.grid(axis="y", alpha=0.3)
    # Annotation: 72.8% at >= 0.85 (derivation.md highlight) — above the bars
    high_conf = sum(c >= 0.85 for c in confs)
    ax.text(0.5, 0.97,
            f"{high_conf}/{n} edge ber-confidence ≥ 0.85  ({100*high_conf/n:.1f}%)",
            transform=ax.transAxes, ha="center", va="top", fontsize=10,
            bbox=dict(facecolor="#e8f5e9", edgecolor="#2e7d32", boxstyle="round,pad=0.4"))
    plt.savefig(out / "fig_confidence_distribution.png")
    plt.close(fig)


# =========================================================================
# Main
# =========================================================================
def main() -> int:
    out = HERE
    print(f"Generating figures into: {out}")
    fig_orphan_rates(out);          print("  - fig_orphan_rates.png")
    fig_type_distribution(out);     print("  - fig_type_distribution.png")
    fig_crossbook_types(out);       print("  - fig_crossbook_types.png")
    fig_subject_pairs(out);         print("  - fig_subject_pairs.png")
    fig_confidence_distribution(out); print("  - fig_confidence_distribution.png")
    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
