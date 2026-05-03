"""Step E: Knowledge Graph Completion via semantic similarity and LLM classification."""

import hashlib
import json
import logging
from collections.abc import Callable
from typing import Literal

from llama_index.core.program import LLMTextCompletionProgram
from pydantic import BaseModel, Field
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from src.cache import cache_manager
from src.config import DEFAULT_EMBEDDING_MODEL, DEFAULT_CHAT_MODEL
from src.graph import get_embedding_dimensions
from src.llama_setup import get_embed_model, get_llm
from src.schema_adapter import SchemaAdapter, SorosAdapter

logger = logging.getLogger(__name__)

# Bump when prompt or schema changes to invalidate classification cache.
# v3: classifier sees each concept's existing graph neighborhood (bab + typed
# out-edges + shared neighbors) in addition to name/description/formula.
CLASSIFICATION_PROMPT_VERSION = "v3"

# Cap out-edges per concept in the prompt to bound prompt size.
NEIGHBORHOOD_MAX_EDGES = 5


def _is_rate_limit_error(exception: BaseException) -> bool:
    """Check if exception is a rate limit error (HTTP 429)."""
    error_str = str(exception).lower()
    if "429" in error_str or "rate limit" in error_str:
        return True
    status = getattr(exception, "status_code", None)
    if status == 429:
        return True
    response = getattr(exception, "response", None)
    if response is not None:
        resp_status = getattr(response, "status_code", None)
        if resp_status == 429:
            return True
    return False


def _is_retriable_error(exception: BaseException) -> bool:
    """Retriable: 429 rate limits, 5xx server errors, and transient network issues."""
    if _is_rate_limit_error(exception):
        return True

    error_str = str(exception).lower()
    # Transient network / server hints
    transient_markers = (
        "timeout",
        "timed out",
        "connection reset",
        "connection aborted",
        "connection error",
        "temporarily unavailable",
        "service unavailable",
        "bad gateway",
        "gateway timeout",
        "502",
        "503",
        "504",
    )
    if any(marker in error_str for marker in transient_markers):
        return True

    status = getattr(exception, "status_code", None)
    if isinstance(status, int) and 500 <= status < 600:
        return True
    response = getattr(exception, "response", None)
    if response is not None:
        resp_status = getattr(response, "status_code", None)
        if isinstance(resp_status, int) and 500 <= resp_status < 600:
            return True

    return False


@retry(
    retry=retry_if_exception(_is_retriable_error),
    wait=wait_exponential(multiplier=2, min=10, max=120),
    stop=stop_after_attempt(5),
    reraise=True,
    before_sleep=lambda retry_state: logger.warning(
        "Transient error, retrying in %.1f seconds (attempt %d/5): %s",
        retry_state.next_action.sleep if retry_state.next_action else 10,
        retry_state.attempt_number,
        retry_state.outcome.exception() if retry_state.outcome else "unknown",
    ),
)
def _get_embeddings_raw(texts: list[str], model: str) -> list[list[float]]:
    """Get embeddings from API without caching."""
    embed_model = get_embed_model(model)
    return embed_model.get_text_embedding_batch(texts)


def build_embed_text(node: dict, adapter: SchemaAdapter | None = None) -> str:
    """Build the text to embed for a node.

    When `adapter` is provided, delegates to its `build_embed_text`. Otherwise
    falls back to the soros-flavored layout (formula/variables/kondisi) for
    backward compat with older callers.
    """
    if adapter is not None:
        return adapter.build_embed_text(node)
    text = f"{node['name']}. {node.get('description', node['name'])}"
    if node.get("formula"):
        text += f" Rumus: {', '.join(node['formula'])}"
    if node.get("variables"):
        text += f" Variabel: {', '.join(node['variables'])}"
    if node.get("kondisi"):
        text += f" Kondisi: {', '.join(node['kondisi'])}"
    return text


def get_embeddings(
    texts: list[str],
    model: str | None = None,
    use_cache: bool = True,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> list[list[float]]:
    """Get embeddings for a list of texts with optional caching."""
    model = model or DEFAULT_EMBEDDING_MODEL
    total = len(texts)

    if not use_cache:
        if progress_callback:
            progress_callback(0, total, "Fetching embeddings from API...")
        result = _get_embeddings_raw(texts, model)
        if progress_callback:
            progress_callback(total, total, "Embeddings complete")
        return result

    embeddings = []
    uncached_indices = []
    uncached_texts = []
    cached_count = 0

    for i, text in enumerate(texts):
        cached = cache_manager.get_embedding(text, model)
        if cached is not None:
            embeddings.append(cached)
            cached_count += 1
            logger.debug("Loaded embedding from cache for text %d", i)
            if progress_callback:
                progress_callback(
                    cached_count,
                    total,
                    f"Loading from cache ({cached_count}/{total})",
                )
        else:
            embeddings.append(None)
            uncached_indices.append(i)
            uncached_texts.append(text)

    if uncached_texts:
        logger.info(
            "Fetching embeddings for %d uncached texts (model: %s)",
            len(uncached_texts),
            model,
        )
        if progress_callback:
            progress_callback(
                cached_count,
                total,
                f"Fetching {len(uncached_texts)} embeddings from API...",
            )

        new_embeddings = _get_embeddings_raw(uncached_texts, model)

        for idx, emb in zip(uncached_indices, new_embeddings):
            embeddings[idx] = emb
            cache_manager.put_embedding(texts[idx], model, emb)
            cached_count += 1
            if progress_callback:
                progress_callback(
                    cached_count,
                    total,
                    f"Embedding {cached_count}/{total}",
                )

    if progress_callback:
        progress_callback(total, total, "Embeddings complete")

    return embeddings


def find_similar_pairs_ann(
    driver,
    nodes: list[dict],
    embeddings: list[list[float]],
    model: str,
    threshold: float = 0.8,
    top_k: int = 10,
    allowed_names: set[str] | None = None,
    progress_callback: Callable[[int, int, str], None] | None = None,
    adapter: SchemaAdapter | None = None,
) -> list[dict]:
    """Find similar pairs using Neo4j Vector Index (ANN search).

    This is O(n log n) instead of O(n²) for the brute-force approach.

    Args:
        driver: Neo4j driver
        nodes: List of dicts with 'name', 'description', 'labels' keys
        embeddings: Corresponding embedding vectors
        model: Embedding model name (for index creation)
        threshold: Minimum similarity score
        top_k: Number of similar nodes to find per query
        allowed_names: If provided, only pairs where BOTH source and target names
            appear in this set are kept. Used by single-doc scope to restrict
            matches to the selected document's nodes even though the vector
            index contains embeddings for the entire graph.
        progress_callback: Optional progress callback
        adapter: SchemaAdapter for the target KG. Defaults to SorosAdapter for
            backward compat.

    Returns list of dicts with 'source', 'target', 'similarity'.
    """
    if adapter is None:
        adapter = SorosAdapter()
    dimensions = get_embedding_dimensions(model)
    if progress_callback:
        progress_callback(0, len(nodes), "Creating vector index...")

    adapter.create_vector_indexes(driver, dimensions=dimensions)

    # Fast path: skip uploading embeddings that Neo4j already has under the
    # same model. The `embedding` property is the source of truth for the
    # vector index; re-setting it with identical bytes is pure overhead.
    node_names = [n["name"] for n in nodes]
    already_current = adapter.get_nodes_with_current_embedding(driver, node_names, model)
    to_store = [
        (n, e) for n, e in zip(nodes, embeddings) if n["name"] not in already_current
    ]

    if to_store:
        if progress_callback:
            progress_callback(
                0,
                len(nodes),
                f"Storing embeddings on {len(to_store)} nodes "
                f"({len(already_current)} already current)...",
            )
        store_nodes = [p[0] for p in to_store]
        store_embs = [p[1] for p in to_store]
        adapter.store_node_embeddings(driver, store_nodes, store_embs, model)
    else:
        logger.info(
            "All %d embeddings already current on Neo4j, skipping upload", len(nodes)
        )
        if progress_callback:
            progress_callback(
                0, len(nodes), "Embeddings already current, skipping upload"
            )

    pairs = []
    seen_pairs: set[tuple[str, str]] = set()
    total = len(nodes)

    for i, (node, emb) in enumerate(zip(nodes, embeddings)):
        if progress_callback:
            progress_callback(i, total, f"Querying similar for {node['name'][:30]}...")

        try:
            similar = adapter.query_similar_nodes(
                driver,
                query_embedding=emb,
                k=top_k,
                threshold=threshold,
                exclude_name=node["name"],
            )
            for s in similar:
                # The vector index covers the whole graph; restrict to the
                # caller's allowed set when given (e.g. single-doc scope).
                if allowed_names is not None and s["name"] not in allowed_names:
                    continue
                pair_key = tuple(sorted([node["name"], s["name"]]))
                if pair_key not in seen_pairs:
                    seen_pairs.add(pair_key)
                    pairs.append(
                        {
                            "source": node["name"],
                            "target": s["name"],
                            "similarity": float(s["score"]),
                        }
                    )
        except Exception as e:
            logger.warning("Failed to query similar for %s: %s", node["name"], e)

    if progress_callback:
        progress_callback(total, total, f"Found {len(pairs)} similar pairs via ANN")

    return pairs


# Classification prompt for typed relationships.
# Bump CLASSIFICATION_PROMPT_VERSION at the top of this module whenever the
# prompt text or schema changes, to invalidate cached classifications.
_CLASSIFICATION_PROMPT = """\
Anda adalah ahli kurikulum yang mengklasifikasikan hubungan antar konsep pembelajaran.

Diberikan dua konsep yang memiliki kemiripan semantik tinggi:

- Konsep A: "{name_a}"
  Deskripsi: "{desc_a}"
  Rumus: {formula_a}
  Variabel: {variables_a}
  Kondisi: {kondisi_a}

- Konsep B: "{name_b}"
  Deskripsi: "{desc_b}"
  Rumus: {formula_b}
  Variabel: {variables_b}
  Kondisi: {kondisi_b}

{neighborhood_block}
Klasifikasikan hubungan antara A dan B sebagai SALAH SATU dari:
1. **isPrerequisiteOf**: A harus dipelajari sebelum B (ketergantungan urutan ketat).
   Contoh: "Bilangan Bulat" → "Persamaan Linear".
2. **supports**: A membantu pemahaman B atau A diterapkan dalam B (ketergantungan fungsional).
   Contoh: "Hukum Newton" → "Gaya Gesek".
3. **analogousTo**: A dan B memiliki pola/prinsip yang sama (hubungan struktural, anti-silo).
   Contoh: "Laju Reaksi Kimia" ↔ "Kecepatan Reaksi Biologis".
4. **none**: Tidak ada hubungan bermakna meski mirip secara semantik.

Gunakan rumus, variabel, dan kondisi untuk membedakan `supports` (berbagi konteks penerapan)
dari `analogousTo` (berbagi struktur tapi konteks berbeda).

Kembalikan JSON dengan field:
- "rel_type": salah satu dari "isPrerequisiteOf", "supports", "analogousTo", "none"
- "confidence": skor 0.0–1.0 menyatakan keyakinan klasifikasi
"""


class Classification(BaseModel):
    """Structured output for a single pair classification."""

    rel_type: Literal["isPrerequisiteOf", "supports", "analogousTo", "none"]
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)


def _format_list(items) -> str:
    """Format a list of strings for prompt inclusion."""
    if not items:
        return "(tidak ada)"
    return ", ".join(str(x) for x in items)


def _format_out_edges(edges: list[dict] | None) -> str:
    if not edges:
        return "  (tidak ada)"
    lines = []
    for e in edges:
        conf = e.get("confidence")
        conf_str = (
            f" (conf: {conf:.2f})" if isinstance(conf, (int, float)) else ""
        )
        lines.append(f'  - {e["rel_type"]} → "{e["target"]}"{conf_str}')
    return "\n".join(lines)


def _compute_shared_neighbors(ctx_a: dict, ctx_b: dict) -> list[str]:
    """Concepts that both A and B already point to via a typed edge."""
    targets_a = {
        e["target"] for e in ctx_a.get("out_edges", []) if e.get("target")
    }
    targets_b = {
        e["target"] for e in ctx_b.get("out_edges", []) if e.get("target")
    }
    return sorted(targets_a & targets_b)


def _build_neighborhood_block(
    name_a: str,
    bab_a: str | None,
    out_edges_a: list[dict] | None,
    name_b: str,
    bab_b: str | None,
    out_edges_b: list[dict] | None,
    shared_neighbors: list[str] | None,
) -> str:
    """Render the KONTEKS GRAF prompt section. Empty string when no signal."""
    if not (bab_a or bab_b or out_edges_a or out_edges_b or shared_neighbors):
        return ""

    if bab_a and bab_b:
        bab_note = (
            "(Bab yang sama)" if bab_a == bab_b else "(Bab berbeda)"
        )
    else:
        bab_note = ""

    return (
        "========================\n"
        "KONTEKS GRAF (HUBUNGAN YANG SUDAH ADA)\n"
        "========================\n"
        f'Konsep A ("{name_a}") berada di Bab: {bab_a or "(tidak diketahui)"}\n'
        f"Hubungan A yang sudah ada di graf:\n"
        f"{_format_out_edges(out_edges_a)}\n\n"
        f'Konsep B ("{name_b}") berada di Bab: {bab_b or "(tidak diketahui)"} '
        f"{bab_note}\n"
        f"Hubungan B yang sudah ada di graf:\n"
        f"{_format_out_edges(out_edges_b)}\n\n"
        f"Tetangga bersama (target yang sama-sama dirujuk A dan B): "
        f"{_format_list(shared_neighbors)}\n\n"
        "Gunakan konteks graf ini sebagai bukti tambahan. Jika A sudah punya "
        "banyak hubungan `isPrerequisiteOf` dengan konsep di Bab yang sama "
        "dengan B, klasifikasi `isPrerequisiteOf` lebih mungkin benar. Tetangga "
        "bersama menandakan A dan B kemungkinan `analogousTo`.\n"
    )


def _context_fingerprint(
    ctx_a: dict, ctx_b: dict, shared_neighbors: list[str]
) -> str:
    """Stable short hash of the neighborhood payload for cache keying."""
    payload = {
        "a": {
            "bab": ctx_a.get("bab"),
            "edges": ctx_a.get("out_edges", []),
        },
        "b": {
            "bab": ctx_b.get("bab"),
            "edges": ctx_b.get("out_edges", []),
        },
        "shared": shared_neighbors,
    }
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(blob.encode("utf-8")).hexdigest()[:12]


_classify_retry = retry(
    retry=retry_if_exception(_is_retriable_error),
    wait=wait_exponential(multiplier=2, min=10, max=120),
    stop=stop_after_attempt(5),
    reraise=True,
    before_sleep=lambda retry_state: logger.warning(
        "Classify transient error, retrying in %.1fs (attempt %d/5): %s",
        retry_state.next_action.sleep if retry_state.next_action else 10,
        retry_state.attempt_number,
        retry_state.outcome.exception() if retry_state.outcome else "unknown",
    ),
)


@_classify_retry
def classify_similar_pair(
    name_a: str,
    desc_a: str,
    name_b: str,
    desc_b: str,
    llm_model: str | None = None,
    formula_a: list[str] | None = None,
    variables_a: list[str] | None = None,
    kondisi_a: list[str] | None = None,
    formula_b: list[str] | None = None,
    variables_b: list[str] | None = None,
    kondisi_b: list[str] | None = None,
    bab_a: str | None = None,
    out_edges_a: list[dict] | None = None,
    bab_b: str | None = None,
    out_edges_b: list[dict] | None = None,
    shared_neighbors: list[str] | None = None,
) -> tuple[str, float]:
    """Use LLM to classify the relationship between two similar konsep.

    Returns a tuple of (rel_type, confidence) where rel_type is one of
    isPrerequisiteOf, supports, analogousTo, or none, and confidence is in [0, 1].
    Retries on 429 / 5xx / transient network errors with exponential backoff.

    Optional neighborhood args (bab, out_edges, shared_neighbors) inject the
    KONTEKS GRAF section so the LLM can use existing typed edges as evidence.
    """
    model = llm_model or DEFAULT_CHAT_MODEL
    llm = get_llm(model)

    program = LLMTextCompletionProgram.from_defaults(
        llm=llm,
        output_cls=Classification,
        prompt_template_str=_CLASSIFICATION_PROMPT,
    )

    neighborhood_block = _build_neighborhood_block(
        name_a=name_a,
        bab_a=bab_a,
        out_edges_a=out_edges_a,
        name_b=name_b,
        bab_b=bab_b,
        out_edges_b=out_edges_b,
        shared_neighbors=shared_neighbors,
    )

    result: Classification = program(
        name_a=name_a,
        desc_a=desc_a or name_a,
        formula_a=_format_list(formula_a),
        variables_a=_format_list(variables_a),
        kondisi_a=_format_list(kondisi_a),
        name_b=name_b,
        desc_b=desc_b or name_b,
        formula_b=_format_list(formula_b),
        variables_b=_format_list(variables_b),
        kondisi_b=_format_list(kondisi_b),
        neighborhood_block=neighborhood_block,
    )
    return result.rel_type, float(result.confidence)


# ── Batched classification ─────────────────────────────────────────

_BATCH_CLASSIFICATION_PROMPT = """\
Anda adalah ahli kurikulum yang mengklasifikasikan hubungan antar konsep pembelajaran.

Untuk SETIAP pasangan konsep berikut, klasifikasikan hubungan antara A dan B sebagai
SALAH SATU dari:
1. **isPrerequisiteOf**: A harus dipelajari sebelum B (ketergantungan urutan ketat).
   Contoh: "Bilangan Bulat" → "Persamaan Linear".
2. **supports**: A membantu pemahaman B atau A diterapkan dalam B (ketergantungan fungsional).
   Contoh: "Hukum Newton" → "Gaya Gesek".
3. **analogousTo**: A dan B memiliki pola/prinsip yang sama (hubungan struktural, anti-silo).
   Contoh: "Laju Reaksi Kimia" ↔ "Kecepatan Reaksi Biologis".
4. **none**: Tidak ada hubungan bermakna meski mirip secara semantik.

Gunakan rumus, variabel, dan kondisi untuk membedakan `supports` (berbagi konteks penerapan)
dari `analogousTo` (berbagi struktur tapi konteks berbeda).

PASANGAN:
{pairs_block}

Kembalikan JSON dengan field "items" berisi array. Setiap elemen harus memiliki:
- "pair_index": int (sesuai index pasangan di atas, dimulai dari 0)
- "rel_type": salah satu dari "isPrerequisiteOf", "supports", "analogousTo", "none"
- "confidence": skor 0.0–1.0 menyatakan keyakinan klasifikasi

WAJIB kembalikan SATU entri untuk SETIAP pasangan (total {n_pairs} entri).
"""


class ClassificationItem(BaseModel):
    """One pair's classification inside a batch response."""

    pair_index: int = Field(ge=0)
    rel_type: Literal["isPrerequisiteOf", "supports", "analogousTo", "none"]
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)


class ClassificationBatch(BaseModel):
    """Structured output for a batch pair classification."""

    items: list[ClassificationItem]


def _format_pair_block(
    index: int,
    info_a: dict,
    info_b: dict,
    shared_neighbors: list[str] | None = None,
) -> str:
    """Render one pair block for the batch prompt.

    info_a/info_b may carry optional `bab` and `out_edges` keys; when present
    a KONTEKS GRAF subsection is appended to the pair block.
    """
    block = (
        f"[{index}]\n"
        f"  Konsep A: \"{info_a['name']}\"\n"
        f"  Deskripsi A: \"{info_a['description'] or info_a['name']}\"\n"
        f"  Rumus A: {_format_list(info_a.get('formula'))}\n"
        f"  Variabel A: {_format_list(info_a.get('variables'))}\n"
        f"  Kondisi A: {_format_list(info_a.get('kondisi'))}\n"
        f"  Konsep B: \"{info_b['name']}\"\n"
        f"  Deskripsi B: \"{info_b['description'] or info_b['name']}\"\n"
        f"  Rumus B: {_format_list(info_b.get('formula'))}\n"
        f"  Variabel B: {_format_list(info_b.get('variables'))}\n"
        f"  Kondisi B: {_format_list(info_b.get('kondisi'))}"
    )

    neighborhood = _build_neighborhood_block(
        name_a=info_a["name"],
        bab_a=info_a.get("bab"),
        out_edges_a=info_a.get("out_edges"),
        name_b=info_b["name"],
        bab_b=info_b.get("bab"),
        out_edges_b=info_b.get("out_edges"),
        shared_neighbors=shared_neighbors,
    )
    if neighborhood:
        # Indent the block so it visually nests under the pair entry.
        indented = "\n".join("  " + line for line in neighborhood.splitlines())
        block += "\n" + indented
    return block


@_classify_retry
def _classify_batch_raw(
    pair_infos: list[tuple[dict, dict]],
    llm_model: str,
    pair_neighborhoods: list[dict] | None = None,
) -> list[ClassificationItem]:
    """Classify a batch of pairs in one LLM call. Retries on transient errors."""
    llm = get_llm(llm_model)
    program = LLMTextCompletionProgram.from_defaults(
        llm=llm,
        output_cls=ClassificationBatch,
        prompt_template_str=_BATCH_CLASSIFICATION_PROMPT,
    )
    blocks = []
    for i, (a, b) in enumerate(pair_infos):
        shared = (
            (pair_neighborhoods[i] or {}).get("shared_neighbors")
            if pair_neighborhoods else None
        )
        blocks.append(_format_pair_block(i, a, b, shared_neighbors=shared))
    pairs_block = "\n\n".join(blocks)
    result: ClassificationBatch = program(
        pairs_block=pairs_block,
        n_pairs=len(pair_infos),
    )
    return result.items


def classify_pairs_batch(
    pair_infos: list[tuple[dict, dict]],
    llm_model: str | None = None,
    pair_neighborhoods: list[dict] | None = None,
) -> list[tuple[str, float]]:
    """Classify a batch of pairs and return aligned [(rel_type, confidence), ...].

    `pair_infos[i]` is `(info_a, info_b)` where each info has keys:
    name, description, formula, variables, kondisi, and optionally
    bab + out_edges (for the KONTEKS GRAF section).

    `pair_neighborhoods[i]` is an optional dict with shared_neighbors per pair.

    The LLM returns items keyed by pair_index; we realign to the input order.
    Missing indices fall back to ("none", 0.0).
    """
    if not pair_infos:
        return []
    model = llm_model or DEFAULT_CHAT_MODEL
    items = _classify_batch_raw(pair_infos, model, pair_neighborhoods)

    by_index: dict[int, tuple[str, float]] = {
        it.pair_index: (it.rel_type, float(it.confidence)) for it in items
    }
    out: list[tuple[str, float]] = []
    for i in range(len(pair_infos)):
        out.append(by_index.get(i, ("none", 0.0)))
    return out


def _classification_cache_text(
    source: str, target: str, fingerprint: str = ""
) -> str:
    """Canonical cache key input — order-invariant so (A,B) and (B,A) share a key.

    When `fingerprint` is set (a hash of the neighborhood payload fed to the
    classifier), it is folded into the key so that re-runs after the graph
    gains new typed edges produce a cache miss and re-classify.
    """
    a, b = sorted([source, target])
    if fingerprint:
        return f"{a}||{b}||ctx:{fingerprint}"
    return f"{a}||{b}"


def classify_similar_pairs(
    driver,
    pairs: list[dict],
    llm_model: str | None = None,
    progress_callback: Callable[[int, int, str], None] | None = None,
    use_cache: bool = True,
    batch_size: int = 1,
    adapter: SchemaAdapter | None = None,
) -> list[dict]:
    """Classify SIMILAR_TO pairs into typed relationships using LLM.

    For each pair, looks up descriptions (and formula/variables/kondisi) from
    Neo4j and calls the LLM to classify the relationship as isPrerequisiteOf,
    supports, analogousTo, or none. Results include a confidence score in [0, 1].

    Classifications are cached on disk by (pair, llm_model, prompt_version) so
    re-runs on the same pairs do not re-bill the LLM. Failures are NOT cached
    and surfaced in the final progress message so the user can rerun to retry.

    Args:
        driver: Neo4j driver (for fetching descriptions)
        pairs: List of {"source": str, "target": str, "similarity": float}
        llm_model: LLM model string
        progress_callback: Optional progress callback
        use_cache: Read/write classification cache (default True)
        batch_size: Number of pairs classified per LLM call. Default 1
            (per-pair mode, preserves old behavior). Values >1 batch pairs into
            one LLM request — much fewer round-trips but slightly more fragile
            per call (if the batch errors, the whole batch retries as a unit).

    Returns list of dicts with source, target, similarity, rel_type, confidence.
    """
    if adapter is None:
        adapter = SorosAdapter()
    total = len(pairs)
    results: list[dict | None] = [None] * total
    model = llm_model or DEFAULT_CHAT_MODEL
    batch_size = max(1, int(batch_size))

    names = list({p["source"] for p in pairs} | {p["target"] for p in pairs})
    node_map = adapter.get_classification_data(driver, names)

    # Neighborhood: parent (bab/chapter) + existing typed out-edges per concept.
    contexts = adapter.get_concept_context(
        driver, names, max_edges=NEIGHBORHOOD_MAX_EDGES
    )

    # Per-pair derived signals — computed once, reused for cache key and prompt.
    pair_ctx: list[dict] = []
    for pair in pairs:
        ctx_a = contexts.get(pair["source"], {"bab": None, "out_edges": []})
        ctx_b = contexts.get(pair["target"], {"bab": None, "out_edges": []})
        shared = _compute_shared_neighbors(ctx_a, ctx_b)
        pair_ctx.append(
            {
                "ctx_a": ctx_a,
                "ctx_b": ctx_b,
                "shared": shared,
                "fingerprint": _context_fingerprint(ctx_a, ctx_b, shared),
            }
        )

    cache_hits = 0
    uncached_indices: list[int] = []

    for i, pair in enumerate(pairs):
        source, target = pair["source"], pair["target"]
        cached = None
        if use_cache:
            cache_text = _classification_cache_text(
                source, target, fingerprint=pair_ctx[i]["fingerprint"]
            )
            cached = cache_manager.get_classification(
                cache_text, model, CLASSIFICATION_PROMPT_VERSION
            )
        if cached is not None:
            results[i] = {
                **pair,
                "rel_type": cached.get("rel_type", "none"),
                "confidence": float(cached.get("confidence", 0.0)),
            }
            cache_hits += 1
        else:
            uncached_indices.append(i)

    if progress_callback and cache_hits:
        progress_callback(
            cache_hits, total, f"Loaded {cache_hits}/{total} from cache"
        )

    def _info_for(name: str, ctx: dict | None = None) -> dict:
        info = node_map.get(name, {})
        ctx = ctx or {}
        return {
            "name": name,
            "description": info.get("description", ""),
            "formula": info.get("formula", []),
            "variables": info.get("variables", []),
            "kondisi": info.get("kondisi", []),
            "bab": ctx.get("bab"),
            "out_edges": ctx.get("out_edges", []),
        }

    failed_count = 0
    processed = cache_hits

    for batch_start in range(0, len(uncached_indices), batch_size):
        batch_idx = uncached_indices[batch_start : batch_start + batch_size]
        batch_pairs = [pairs[j] for j in batch_idx]
        pair_infos = [
            (
                _info_for(p["source"], pair_ctx[j]["ctx_a"]),
                _info_for(p["target"], pair_ctx[j]["ctx_b"]),
            )
            for j, p in zip(batch_idx, batch_pairs)
        ]
        batch_neighborhoods = [
            {"shared_neighbors": pair_ctx[j]["shared"]} for j in batch_idx
        ]

        if progress_callback:
            end = processed + len(batch_idx)
            progress_callback(
                processed,
                total,
                f"Classifying pairs {processed + 1}–{end}/{total}"
                + (f" (batch {len(batch_idx)})" if batch_size > 1 else ""),
            )

        try:
            if batch_size == 1:
                info_a, info_b = pair_infos[0]
                rel_type, confidence = classify_similar_pair(
                    name_a=info_a["name"],
                    desc_a=info_a["description"],
                    name_b=info_b["name"],
                    desc_b=info_b["description"],
                    llm_model=model,
                    formula_a=info_a["formula"],
                    variables_a=info_a["variables"],
                    kondisi_a=info_a["kondisi"],
                    formula_b=info_b["formula"],
                    variables_b=info_b["variables"],
                    kondisi_b=info_b["kondisi"],
                    bab_a=info_a.get("bab"),
                    out_edges_a=info_a.get("out_edges"),
                    bab_b=info_b.get("bab"),
                    out_edges_b=info_b.get("out_edges"),
                    shared_neighbors=batch_neighborhoods[0]["shared_neighbors"],
                )
                outcomes = [(rel_type, confidence)]
            else:
                outcomes = classify_pairs_batch(
                    pair_infos,
                    llm_model=model,
                    pair_neighborhoods=batch_neighborhoods,
                )
        except Exception as e:
            logger.warning(
                "Batch classify failed for pairs %d–%d (%d pairs): %s",
                batch_idx[0],
                batch_idx[-1],
                len(batch_idx),
                e,
            )
            # Don't poison the cache with failures — leave them uncached and
            # surfaced as failed so a rerun retries them.
            for j, pair in zip(batch_idx, batch_pairs):
                results[j] = {**pair, "rel_type": "none", "confidence": 0.0}
            failed_count += len(batch_idx)
            processed += len(batch_idx)
            continue

        for j, pair, (rel_type, confidence) in zip(batch_idx, batch_pairs, outcomes):
            results[j] = {
                **pair,
                "rel_type": rel_type,
                "confidence": confidence,
            }
            if use_cache:
                cache_text = _classification_cache_text(
                    pair["source"],
                    pair["target"],
                    fingerprint=pair_ctx[j]["fingerprint"],
                )
                cache_manager.put_classification(
                    cache_text,
                    model,
                    CLASSIFICATION_PROMPT_VERSION,
                    {"rel_type": rel_type, "confidence": confidence},
                )

        processed += len(batch_idx)

    # Belt-and-suspenders: should never trigger given the loop above.
    final_results: list[dict] = []
    for i, r in enumerate(results):
        if r is None:
            final_results.append(
                {**pairs[i], "rel_type": "none", "confidence": 0.0}
            )
        else:
            final_results.append(r)

    if progress_callback:
        msg = f"Classified {total} pairs ({cache_hits} cached"
        if failed_count:
            msg += f", {failed_count} failed — rerun to retry"
        msg += ")"
        progress_callback(total, total, msg)

    logger.info(
        "Classification done: total=%d, cache_hits=%d, failed=%d, batch_size=%d, model=%s",
        total,
        cache_hits,
        failed_count,
        batch_size,
        model,
    )

    return final_results
