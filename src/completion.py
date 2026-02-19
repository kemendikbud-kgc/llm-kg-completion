"""Step E: Knowledge Graph Completion via semantic similarity."""

from sklearn.metrics.pairwise import cosine_similarity
import litellm
import numpy as np

from src.config import DEFAULT_EMBEDDING_MODEL


def get_embeddings(texts: list[str], model: str | None = None) -> np.ndarray:
    model = model or DEFAULT_EMBEDDING_MODEL
    response = litellm.embedding(model=model, input=texts)
    return np.array([item["embedding"] for item in response.data])


def find_similar_pairs(
    names: list[str],
    descriptions: list[str],
    threshold: float = 0.8,
    embedding_model: str | None = None,
) -> list[dict]:
    embeddings = get_embeddings(descriptions, model=embedding_model)
    sim_matrix = cosine_similarity(embeddings)

    pairs = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            if sim_matrix[i][j] >= threshold:
                pairs.append({
                    "source": names[i],
                    "target": names[j],
                    "similarity": float(sim_matrix[i][j]),
                })
    return pairs
