"""
Generate a 2D UMAP visualization of concept embeddings showing
ANN candidate retrieval for the thesis (Section 4.1.4).

Uses litellm to embed concept descriptions, UMAP for dimensionality
reduction, and matplotlib for the publication-quality figure.
"""

import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path
from litellm import embedding as litellm_embedding
from dotenv import load_dotenv

load_dotenv()

BASE = Path(__file__).resolve().parent.parent / "knowledge_graph_states" / "extraction-v4-validated-byCC"

GRADE_COLORS = {
    "Biologi Kelas XII": "#2ecc71",
    "Fisika Kelas XII": "#3498db",
    "Kimia Kelas XII": "#e67e22",
}
GRADE_SHORT = {
    "Biologi Kelas XII": "Biologi",
    "Fisika Kelas XII": "Fisika",
    "Kimia Kelas XII": "Kimia",
}

def load_concepts():
    concepts = []
    for fname in ["Biologi Kelas XII.json", "Fisika Kelas XII.json", "Kimia Kelas XII.json"]:
        data = json.loads((BASE / fname).read_text(encoding="utf-8"))
        grade = data["grade"]
        for ch in data["chapters"]:
            for st in ch["subtopics"]:
                for c in st["concepts"]:
                    concepts.append({
                        "name": c["name"],
                        "description": c.get("description", ""),
                        "grade": grade,
                        "chapter": ch["chapter"],
                    })
    return concepts


def embed_texts(texts, model="gemini/gemini-embedding-001", batch_size=50):
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        resp = litellm_embedding(model=model, input=batch)
        for item in resp.data:
            all_embeddings.append(item["embedding"])
        print(f"  Embedded {min(i+batch_size, len(texts))}/{len(texts)}")
    return np.array(all_embeddings)


def find_cross_book_pairs(embeddings, concepts, threshold=0.75, top_k=5):
    from sklearn.metrics.pairwise import cosine_similarity
    sim_matrix = cosine_similarity(embeddings)
    pairs = []
    for i in range(len(concepts)):
        scores = sim_matrix[i]
        top_indices = np.argsort(scores)[::-1]
        count = 0
        for j in top_indices:
            if i == j:
                continue
            if concepts[i]["grade"] == concepts[j]["grade"]:
                continue
            if scores[j] < threshold:
                break
            pairs.append((i, j, scores[j]))
            count += 1
            if count >= top_k:
                break
    return pairs


def main():
    print("Loading concepts...")
    concepts = load_concepts()
    print(f"  {len(concepts)} concepts loaded")

    texts = [f"{c['name']}: {c['description']}" for c in concepts]

    cache_path = BASE.parent / "embedding_cache_for_diagram.npz"
    if cache_path.exists():
        print("Loading cached embeddings...")
        cached = np.load(cache_path)
        embeddings = cached["embeddings"]
        if len(embeddings) != len(concepts):
            print("  Cache size mismatch, re-embedding...")
            embeddings = None
        else:
            print(f"  Loaded {len(embeddings)} cached embeddings")
    else:
        embeddings = None

    if embeddings is None:
        print("Embedding concepts via Gemini...")
        embeddings = embed_texts(texts)
        np.savez(cache_path, embeddings=embeddings)
        print(f"  Cached to {cache_path}")

    print("Finding cross-book pairs (threshold=0.75)...")
    pairs = find_cross_book_pairs(embeddings, concepts, threshold=0.75, top_k=3)
    print(f"  {len(pairs)} cross-book pairs found")

    # Deduplicate symmetric pairs
    seen = set()
    unique_pairs = []
    for i, j, score in pairs:
        key = tuple(sorted([i, j]))
        if key not in seen:
            seen.add(key)
            unique_pairs.append((i, j, score))
    pairs = unique_pairs
    print(f"  {len(pairs)} unique pairs after dedup")

    print("Running UMAP...")
    import umap
    reducer = umap.UMAP(n_components=2, random_state=42, n_neighbors=15, min_dist=0.3, metric="cosine")
    coords = reducer.fit_transform(embeddings)

    # Pick a query concept to highlight (one with cross-book hits)
    query_idx = None
    query_pairs = []
    for i, j, score in sorted(pairs, key=lambda x: -x[2]):
        i_pairs = [(ii, jj, ss) for ii, jj, ss in pairs if ii == i or jj == i]
        if len(i_pairs) >= 2:
            query_idx = i
            query_pairs = i_pairs
            break

    if query_idx is None and pairs:
        query_idx = pairs[0][0]
        query_pairs = [pairs[0]]

    print(f"  Query concept: {concepts[query_idx]['name']} ({concepts[query_idx]['grade']})")
    for _, j, s in query_pairs:
        target = j if j != query_idx else _
        print(f"    -> {concepts[target]['name']} ({concepts[target]['grade']}) sim={s:.3f}")

    # Plot
    print("Generating figure...")
    fig, ax = plt.subplots(1, 1, figsize=(12, 8), dpi=150)
    fig.patch.set_facecolor("white")

    # Plot all concepts as dots
    for grade, color in GRADE_COLORS.items():
        mask = [c["grade"] == grade for c in concepts]
        idxs = [i for i, m in enumerate(mask) if m]
        ax.scatter(
            coords[idxs, 0], coords[idxs, 1],
            c=color, alpha=0.4, s=25, edgecolors="none",
            label=GRADE_SHORT[grade], zorder=2
        )

    # Draw ALL cross-book edges (faint)
    for i, j, score in pairs:
        if i == query_idx or j == query_idx:
            continue
        ax.plot(
            [coords[i, 0], coords[j, 0]],
            [coords[i, 1], coords[j, 1]],
            color="#cccccc", linewidth=0.5, alpha=0.3, zorder=1
        )

    # Draw query concept's edges (bold)
    for ii, jj, score in query_pairs:
        target = jj if jj != query_idx else ii
        ax.plot(
            [coords[query_idx, 0], coords[target, 0]],
            [coords[query_idx, 1], coords[target, 1]],
            color="#e74c3c", linewidth=2.0, alpha=0.8, zorder=4
        )
        mid_x = (coords[query_idx, 0] + coords[target, 0]) / 2
        mid_y = (coords[query_idx, 1] + coords[target, 1]) / 2
        ax.annotate(
            f"sim={score:.2f}",
            (mid_x, mid_y),
            fontsize=7, color="#c0392b", ha="center",
            bbox=dict(boxstyle="round,pad=0.2", facecolor="white", edgecolor="#e74c3c", alpha=0.9),
            zorder=6
        )
        # Label target with spread offsets to avoid overlap
        offsets = [(15, 20), (-15, -25), (15, -20), (-15, 25)]
        t_idx_in_loop = query_pairs.index((ii, jj, score))
        ox, oy = offsets[t_idx_in_loop % len(offsets)]
        ax.annotate(
            concepts[target]["name"],
            (coords[target, 0], coords[target, 1]),
            xytext=(ox, oy), textcoords="offset points",
            fontsize=8, color=GRADE_COLORS[concepts[target]["grade"]],
            fontweight="bold", zorder=6,
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="gray", alpha=0.9),
            arrowprops=dict(arrowstyle="-", color="gray", alpha=0.5),
        )

    # Highlight query concept
    ax.scatter(
        [coords[query_idx, 0]], [coords[query_idx, 1]],
        c="#e74c3c", s=200, edgecolors="black", linewidths=2,
        marker="*", zorder=5
    )
    ax.annotate(
        f"Query: {concepts[query_idx]['name']}",
        (coords[query_idx, 0], coords[query_idx, 1]),
        xytext=(-20, -30), textcoords="offset points",
        fontsize=9, fontweight="bold", color="#e74c3c",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white", edgecolor="#e74c3c", alpha=0.95),
        arrowprops=dict(arrowstyle="->", color="#e74c3c", lw=1.5),
        zorder=6
    )

    # Legend and labels
    ax.legend(loc="upper left", fontsize=10, framealpha=0.9)
    ax.set_title(
        "Visualisasi ANN: Candidate Retrieval Lintas-Buku\n"
        f"(UMAP 2D projection, {len(concepts)} konsep, threshold $\\tau$ = 0.75)",
        fontsize=13, fontweight="bold", pad=15
    )
    ax.set_xlabel("UMAP-1", fontsize=10)
    ax.set_ylabel("UMAP-2", fontsize=10)
    ax.tick_params(labelsize=8)

    # Info box
    info_text = (
        f"Embedding: Gemini Embedding 001 (d=3072)\n"
        f"Pairs found: {len(pairs)} cross-book (sim $\\geq$ 0.75)\n"
        f"Index: HNSW (M=16, ef_construction=100)"
    )
    ax.text(
        0.98, 0.98, info_text,
        transform=ax.transAxes, fontsize=8, va="top", ha="right",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#f8f9fa", edgecolor="#dee2e6", alpha=0.9)
    )

    plt.tight_layout()
    out_path = BASE.parent / "ann_candidate_retrieval_visual.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="white")
    print(f"\nSaved to {out_path}")
    plt.close()


if __name__ == "__main__":
    main()
