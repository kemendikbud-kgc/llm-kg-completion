"""Step E: Knowledge Graph Completion via semantic similarity."""

import numpy as np

from src.config import DEFAULT_EMBEDDING_MODEL
from src.llama_setup import get_embed_model


def cosine_similarity(a: list[float], b: list[float]) -> float:
    a_arr = np.array(a)
    b_arr = np.array(b)
    return float(np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr)))


def get_embeddings(texts: list[str], model: str | None = None) -> list[list[float]]:
    """Get embeddings for a list of texts using LlamaIndex LiteLLMEmbedding."""
    model = model or DEFAULT_EMBEDDING_MODEL
    embed_model = get_embed_model(model)
    return embed_model.get_text_embedding_batch(texts)


def find_similar_pairs(
    names: list[str],
    descriptions: list[str],
    threshold: float = 0.8,
    embedding_model: str | None = None,
) -> list[dict]:
    embeddings = get_embeddings(descriptions, model=embedding_model)

    pairs = []
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
    return pairs
