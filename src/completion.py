"""Step E: Knowledge Graph Completion via semantic similarity."""

from sklearn.metrics.pairwise import cosine_similarity
from openai import OpenAI
import numpy as np

from src.config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)


def get_embeddings(texts: list[str]) -> np.ndarray:
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=texts,
    )
    return np.array([e.embedding for e in response.data])


def find_similar_pairs(names: list[str], descriptions: list[str], threshold: float = 0.8) -> list[dict]:
    embeddings = get_embeddings(descriptions)
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
