"""LlamaIndex + litellm wiring: LLM and embedding model factories."""

from llama_index.llms.litellm import LiteLLM
from llama_index.embeddings.litellm import LiteLLMEmbedding


def get_llm(model: str) -> LiteLLM:
    """Return a LlamaIndex LLM backed by litellm."""
    return LiteLLM(model=model, temperature=0.1)


def get_embed_model(model: str) -> LiteLLMEmbedding:
    """Return a LlamaIndex embedding model backed by litellm."""
    return LiteLLMEmbedding(model_name=model)
