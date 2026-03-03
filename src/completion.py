"""Step E: Knowledge Graph Completion via semantic similarity and LLM classification."""

import logging
from collections.abc import Callable

import numpy as np
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from src.cache import cache_manager
from src.config import DEFAULT_EMBEDDING_MODEL, DEFAULT_CHAT_MODEL
from src.llama_setup import get_embed_model, get_llm

logger = logging.getLogger(__name__)


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


def cosine_similarity(a: list[float], b: list[float]) -> float:
    a_arr = np.array(a)
    b_arr = np.array(b)
    return float(np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr)))


@retry(
    retry=retry_if_exception(_is_rate_limit_error),
    wait=wait_exponential(multiplier=2, min=10, max=120),
    stop=stop_after_attempt(5),
    reraise=True,
    before_sleep=lambda retry_state: logger.warning(
        "Rate limit hit, retrying in %.1f seconds (attempt %d/5)",
        retry_state.next_action.sleep if retry_state.next_action else 10,
        retry_state.attempt_number,
    ),
)
def _get_embeddings_raw(texts: list[str], model: str) -> list[list[float]]:
    """Get embeddings from API without caching."""
    embed_model = get_embed_model(model)
    return embed_model.get_text_embedding_batch(texts)


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


def find_similar_pairs(
    names: list[str],
    descriptions: list[str],
    threshold: float = 0.8,
    embedding_model: str | None = None,
    progress_callback: Callable[[int, int, str], None] | None = None,
    min_description_length: int = 10,
) -> list[dict]:
    """Find similar pairs of nodes based on embedding similarity.

    Returns list of dicts with 'source', 'target', 'similarity'.
    """
    # Filter out nodes with short descriptions
    filtered_indices = []
    filtered_names = []
    filtered_descriptions = []
    skipped_count = 0

    for i, (name, desc) in enumerate(zip(names, descriptions)):
        if desc and len(desc.strip()) >= min_description_length:
            filtered_indices.append(i)
            filtered_names.append(name)
            filtered_descriptions.append(desc)
        else:
            skipped_count += 1

    if skipped_count > 0:
        logger.info(
            "Skipped %d nodes with descriptions < %d chars",
            skipped_count,
            min_description_length,
        )

    names = filtered_names
    descriptions = filtered_descriptions

    if len(names) < 2:
        logger.warning("Not enough nodes with valid descriptions to compare")
        return []

    if progress_callback:
        progress_callback(0, 1, "Computing embeddings...")

    combined_texts = [f"{name}. {desc}" for name, desc in zip(names, descriptions)]
    embeddings = get_embeddings(combined_texts, model=embedding_model)

    n = len(names)
    total_pairs = n * (n - 1) // 2
    pairs = []
    checked = 0

    if progress_callback:
        progress_callback(0, total_pairs, f"Comparing {total_pairs} pairs...")

    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            score = cosine_similarity(embeddings[i], embeddings[j])
            if score >= threshold:
                pairs.append(
                    {
                        "source": names[i],
                        "target": names[j],
                        "similarity": float(score),
                    }
                )
            checked += 1
            if progress_callback and checked % 100 == 0:
                progress_callback(
                    checked, total_pairs, f"Comparing pairs ({checked}/{total_pairs})"
                )

    if progress_callback:
        progress_callback(total_pairs, total_pairs, f"Found {len(pairs)} similar pairs")

    return pairs


# Classification prompt for typed relationships
_CLASSIFICATION_PROMPT = """\
Anda adalah ahli kurikulum yang mengklasifikasikan hubungan antar konsep pembelajaran.

Diberikan dua konsep yang memiliki kemiripan semantik tinggi:
- Konsep A: "{name_a}"
  Deskripsi: "{desc_a}"
- Konsep B: "{name_b}"
  Deskripsi: "{desc_b}"

Klasifikasikan hubungan antara A dan B sebagai SALAH SATU dari:
1. **isPrerequisiteOf**: A harus dipelajari sebelum B (ketergantungan urutan ketat)
   Contoh: "Bilangan Bulat" → "Persamaan Linear"
2. **supports**: A membantu pemahaman B atau A diterapkan dalam B (ketergantungan fungsional)
   Contoh: "Hukum Newton" → "Gaya Gesek"
3. **analogousTo**: A dan B memiliki pola/prinsip yang sama (hubungan struktural, anti-silo)
   Contoh: "Laju Reaksi Kimia" ↔ "Kecepatan Reaksi Biologis"
4. **none**: Tidak ada hubungan bermakna meski mirip secara semantik

Jawab HANYA dengan satu kata: isPrerequisiteOf, supports, analogousTo, atau none.
Jangan tambahkan penjelasan."""


def classify_similar_pair(
    name_a: str,
    desc_a: str,
    name_b: str,
    desc_b: str,
    llm_model: str | None = None,
) -> str:
    """Use LLM to classify the relationship between two similar konsep.

    Returns one of: isPrerequisiteOf, supports, analogousTo, none
    """
    model = llm_model or DEFAULT_CHAT_MODEL
    llm = get_llm(model)

    prompt = _CLASSIFICATION_PROMPT.format(
        name_a=name_a,
        desc_a=desc_a or name_a,
        name_b=name_b,
        desc_b=desc_b or name_b,
    )

    response = llm.complete(prompt)
    answer = response.text.strip().lower()

    # Normalize to valid types
    if "isprerequisiteof" in answer or "prerequisite" in answer:
        return "isPrerequisiteOf"
    elif "supports" in answer or "support" in answer:
        return "supports"
    elif "analogousto" in answer or "analogous" in answer:
        return "analogousTo"
    else:
        return "none"


def classify_similar_pairs(
    driver,
    pairs: list[dict],
    llm_model: str | None = None,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> list[dict]:
    """Classify SIMILAR_TO pairs into typed relationships using LLM.

    For each pair, looks up descriptions from Neo4j and calls LLM to classify
    the relationship as isPrerequisiteOf, supports, analogousTo, or none.

    Args:
        driver: Neo4j driver (for fetching descriptions)
        pairs: List of {"source": str, "target": str, "similarity": float}
        llm_model: LLM model string
        progress_callback: Optional progress callback

    Returns list of dicts with source, target, similarity, rel_type.
    """
    total = len(pairs)
    results = []

    # Fetch all descriptions in one query for efficiency
    names = list({p["source"] for p in pairs} | {p["target"] for p in pairs})
    desc_map: dict[str, str] = {}

    with driver.session() as session:
        result = session.run(
            """
            MATCH (n) WHERE n.name IN $names AND (n:Konsep OR n:SubKonsep)
            RETURN n.name AS name, n.description AS description
            """,
            names=names,
        )
        for r in result:
            desc_map[r["name"]] = r["description"] or ""

    for i, pair in enumerate(pairs):
        if progress_callback:
            progress_callback(i, total, f"Classifying pair {i + 1}/{total}...")

        source, target = pair["source"], pair["target"]
        try:
            rel_type = classify_similar_pair(
                name_a=source,
                desc_a=desc_map.get(source, ""),
                name_b=target,
                desc_b=desc_map.get(target, ""),
                llm_model=llm_model,
            )
        except Exception as e:
            logger.warning("Failed to classify %s <-> %s: %s", source, target, e)
            rel_type = "none"

        results.append({**pair, "rel_type": rel_type})

    if progress_callback:
        progress_callback(total, total, f"Classified {total} pairs")

    return results
