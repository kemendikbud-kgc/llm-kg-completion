"""Step E: Knowledge Graph Completion via semantic similarity."""

import hashlib
import json
import logging
from collections.abc import Callable
from pathlib import Path

import numpy as np
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from src.config import DEFAULT_EMBEDDING_MODEL
from src.llama_setup import get_embed_model

logger = logging.getLogger(__name__)

EMBEDDING_CACHE_DIR = Path("data/embedding_cache")


def _embedding_cache_key(text: str, model: str) -> str:
    """Return SHA-256 hash of text + model for cache keying."""
    return hashlib.sha256((text + model).encode()).hexdigest()


def _load_embedding_from_cache(cache_key: str) -> list[float] | None:
    """Load embedding from cache if exists."""
    cache_file = EMBEDDING_CACHE_DIR / f"{cache_key}.json"
    if cache_file.exists():
        data = json.loads(cache_file.read_text(encoding="utf-8"))
        return data.get("embedding")
    return None


def _save_embedding_to_cache(cache_key: str, embedding: list[float]) -> None:
    """Save embedding to cache."""
    EMBEDDING_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = EMBEDDING_CACHE_DIR / f"{cache_key}.json"
    cache_file.write_text(
        json.dumps({"embedding": embedding}, indent=2), encoding="utf-8"
    )


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
    """Get embeddings for a list of texts with optional caching.

    Args:
        texts: List of texts to embed
        model: Embedding model string
        use_cache: Whether to use disk cache (default True)
        progress_callback: Optional callback(current, total, message) for progress

    Returns:
        List of embedding vectors
    """
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
        cache_key = _embedding_cache_key(text, model)
        cached = _load_embedding_from_cache(cache_key)
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
            cache_key = _embedding_cache_key(texts[idx], model)
            _save_embedding_to_cache(cache_key, emb)
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

    Args:
        names: List of node names
        descriptions: List of node descriptions (for embedding)
        threshold: Minimum similarity score (default 0.8)
        embedding_model: Embedding model to use
        progress_callback: Optional callback(current, total, message) for progress
        min_description_length: Skip nodes with descriptions shorter than this

    Returns:
        List of dicts with 'source', 'target', 'similarity'
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

    # Combine name + description for richer semantic representation (per paper)
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
