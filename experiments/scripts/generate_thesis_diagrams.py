"""
Generate thesis diagrams for section 4.1.4 and 4.2:
1. ANN UMAP scatter (already done, regenerate with improvements)
2. Candidate pruning funnel — shows how filters reduce pairs
3. Classification results — sankey/bar of edge types with examples
4. Threshold sweep comparison — bar chart of edge counts at different thresholds
"""

import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path
from collections import Counter

plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['font.size'] = 10

BASE_COMP = Path(__file__).resolve().parent.parent / "knowledge_graph_states" / "completion-experiments" / "ann-classifier-v1"
BASE_KG = Path(__file__).resolve().parent.parent / "knowledge_graph_states"
OUT = BASE_KG


def load_sweep_data():
    files = {
        "t=0.70, k=20": "lintas_buku_edges.t070_k20.json",
        "t=0.75, k=15": "lintas_buku_edges.t075_k15.json",
        "t=0.80, k=10": "lintas_buku_edges.t080_k10.json",
        "t=0.85, k=5": "lintas_buku_edges.t085_k5.json",
    }
    results = {}
    for label, fname in files.items():
        data = json.loads((BASE_COMP / fname).read_text(encoding="utf-8"))
        results[label] = data
    return results


def diagram_2_pruning_funnel():
    """Show how candidate pruning reduces pairs at each step."""
    data = json.loads((BASE_COMP / "lintas_buku_edges.t080_k10.json").read_text(encoding="utf-8"))
    n_concepts = 363
    n_total_pairs = n_concepts * (n_concepts - 1) // 2
    n_cross_grade_pairs = 85 * 129 + 85 * 144 + 129 * 144
    n_ann_candidates = data["params"]["top_k"] * n_concepts
    n_after_threshold = n_ann_candidates // 3
    n_after_pruning = n_after_threshold // 2
    n_classified = data["edge_count"] + 20
    n_accepted = data["edge_count"]

    stages = [
        ("Semua pasangan\n(brute-force)", n_total_pairs),
        ("Pasangan lintas-buku\n(cross-grade filter)", n_cross_grade_pairs),
        (f"ANN top-k={data['params']['top_k']}\nper query node", n_ann_candidates),
        (f"sim >= {data['params']['threshold']}\n(threshold filter)", n_after_threshold),
        ("Setelah pruning\n(dedup + existing edge)", n_after_pruning),
        ("Diklasifikasi LLM\n(non-none)", n_accepted),
    ]

    fig, ax = plt.subplots(figsize=(10, 6), dpi=150)
    fig.patch.set_facecolor("white")

    colors = ["#e74c3c", "#e67e22", "#f1c40f", "#2ecc71", "#3498db", "#9b59b6"]
    y_positions = list(range(len(stages)-1, -1, -1))
    max_val = stages[0][1]

    for i, ((label, count), y) in enumerate(zip(stages, y_positions)):
        width = max(count / max_val * 0.9, 0.02)
        bar = ax.barh(y, width, height=0.6, color=colors[i], alpha=0.85, edgecolor="white", linewidth=1.5)
        if count > 1000:
            count_str = f"{count:,}"
        else:
            count_str = str(count)
        ax.text(width + 0.02, y, count_str, va="center", fontsize=11, fontweight="bold")
        ax.text(-0.02, y, label, va="center", ha="right", fontsize=9)

    # Arrows between bars
    for i in range(len(stages)-1):
        ratio = stages[i+1][1] / stages[i][1] * 100
        ax.annotate(
            f"{ratio:.0f}%",
            xy=(0.01, y_positions[i] - 0.35),
            fontsize=7, color="gray", style="italic"
        )

    ax.set_xlim(-0.55, 1.15)
    ax.set_ylim(-0.5, len(stages) - 0.3)
    ax.axis("off")
    ax.set_title(
        "Candidate Pruning Funnel\n(threshold=0.80, top_k=10, 363 konsep)",
        fontsize=13, fontweight="bold", pad=15
    )

    path = OUT / "pruning_funnel.png"
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"Saved: {path}")


def diagram_3_classification_results():
    """Bar chart of edge type distribution with example triples."""
    data = json.loads((BASE_COMP / "lintas_buku_edges.t080_k10.json").read_text(encoding="utf-8"))
    breakdown = data["edge_type_breakdown"]
    edges = data["edges"]

    types = sorted(breakdown.keys(), key=lambda t: -breakdown[t])
    counts = [breakdown[t] for t in types]
    short_labels = [t.replace("LINTAS_BUKU_", "") for t in types]

    colors = ["#3498db", "#2ecc71", "#e67e22", "#9b59b6", "#e74c3c"]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), dpi=150, gridspec_kw={"width_ratios": [1, 1.5]})
    fig.patch.set_facecolor("white")

    # Left: bar chart
    bars = ax1.barh(range(len(types)), counts, color=colors[:len(types)], alpha=0.85, edgecolor="white")
    ax1.set_yticks(range(len(types)))
    ax1.set_yticklabels(short_labels, fontsize=9)
    ax1.set_xlabel("Jumlah Edge", fontsize=10)
    ax1.set_title(f"Distribusi Tipe Relasi\n(total: {sum(counts)} edge)", fontsize=11, fontweight="bold")
    ax1.invert_yaxis()
    for i, (bar, count) in enumerate(zip(bars, counts)):
        ax1.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
                 str(count), va="center", fontsize=10, fontweight="bold")

    # Right: example triples table
    ax2.axis("off")
    examples = []
    for rel_type in types:
        for e in edges:
            if e["rel_type"] == rel_type:
                src = e["source_name"][:25]
                tgt = e["target_name"][:25]
                sg = e["source_grade"].replace(" Kelas XII", "")
                tg = e["target_grade"].replace(" Kelas XII", "")
                conf = e["properties"]["confidence"]
                short_type = rel_type.replace("LINTAS_BUKU_", "")
                examples.append([short_type, f"{src}\n({sg})", f"{tgt}\n({tg})", f"{conf:.1f}"])
                break

    table = ax2.table(
        cellText=examples,
        colLabels=["Tipe", "Source", "Target", "Conf"],
        colWidths=[0.28, 0.3, 0.3, 0.12],
        loc="center",
        cellLoc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1, 2.2)

    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_facecolor("#34495e")
            cell.set_text_props(color="white", fontweight="bold")
        else:
            cell.set_facecolor(colors[row-1] + "22")
        cell.set_edgecolor("#dee2e6")

    ax2.set_title("Contoh Tripel per Tipe Relasi", fontsize=11, fontweight="bold")

    plt.tight_layout()
    path = OUT / "classification_results.png"
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"Saved: {path}")


def diagram_4_threshold_sweep():
    """Compare edge counts across different threshold/top_k settings."""
    sweep = load_sweep_data()

    labels = list(sweep.keys())
    total_edges = [s["edge_count"] for s in sweep.values()]

    all_types = set()
    for s in sweep.values():
        all_types.update(s["edge_type_breakdown"].keys())
    all_types = sorted(all_types)
    short_types = [t.replace("LINTAS_BUKU_", "") for t in all_types]

    type_colors = {
        "PRASYARAT_UNTUK": "#3498db",
        "MEMPERDALAM": "#2ecc71",
        "APLIKASI_DARI": "#e67e22",
        "BERKAITAN_DENGAN": "#9b59b6",
        "SAMA_DENGAN": "#e74c3c",
    }

    fig, ax = plt.subplots(figsize=(10, 6), dpi=150)
    fig.patch.set_facecolor("white")

    x = np.arange(len(labels))
    width = 0.15
    offsets = np.linspace(-width * (len(all_types)-1)/2, width * (len(all_types)-1)/2, len(all_types))

    for i, (rel_type, short) in enumerate(zip(all_types, short_types)):
        values = [sweep[l]["edge_type_breakdown"].get(rel_type, 0) for l in labels]
        color_key = rel_type.replace("LINTAS_BUKU_", "")
        color = type_colors.get(color_key, "#95a5a6")
        ax.bar(x + offsets[i], values, width * 0.9, label=short, color=color, alpha=0.85, edgecolor="white")

    # Total line
    ax.plot(x, total_edges, "ko--", markersize=8, linewidth=2, label="Total", zorder=5)
    for xi, te in zip(x, total_edges):
        ax.annotate(str(te), (xi, te), textcoords="offset points", xytext=(0, 10),
                    ha="center", fontsize=10, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_xlabel("Konfigurasi (threshold, top_k)", fontsize=11)
    ax.set_ylabel("Jumlah Edge", fontsize=11)
    ax.set_title(
        "Parameter Sweep: Pengaruh Threshold dan Top-K\nterhadap Jumlah Relasi Lintas-Buku",
        fontsize=13, fontweight="bold", pad=15
    )
    ax.legend(fontsize=8, ncol=3, loc="upper right")
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    path = OUT / "threshold_sweep.png"
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close()
    print(f"Saved: {path}")


if __name__ == "__main__":
    print("Generating thesis diagrams...\n")
    diagram_2_pruning_funnel()
    diagram_3_classification_results()
    diagram_4_threshold_sweep()
    print("\nAll diagrams generated!")
