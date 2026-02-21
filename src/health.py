"""Health check utilities for verifying API connections."""

from dataclasses import dataclass

from src.config import (
    GOOGLE_API_KEY,
    OPENAI_API_KEY,
    ANTHROPIC_API_KEY,
    ZHIPUAI_API_KEY,
    HUGGINGFACE_API_KEY,
    NEO4J_URI,
    NEO4J_PASSWORD,
    DEFAULT_CHAT_MODEL,
    DEFAULT_EMBEDDING_MODEL,
)
from src.llama_setup import get_llm, get_embed_model


@dataclass
class HealthStatus:
    service: str
    ok: bool
    message: str


def check_neo4j() -> HealthStatus:
    if not NEO4J_URI or not NEO4J_PASSWORD:
        return HealthStatus("Neo4j", False, "Missing NEO4J_URI or NEO4J_PASSWORD")
    try:
        from neo4j import GraphDatabase

        uri: str = NEO4J_URI
        pwd: str = NEO4J_PASSWORD
        driver = GraphDatabase.driver(uri, auth=("neo4j", pwd))
        with driver.session() as session:
            session.run("RETURN 1").single()
        driver.close()
        return HealthStatus("Neo4j", True, "Connected")
    except Exception as e:
        return HealthStatus("Neo4j", False, str(e))


def check_llm(model: str = DEFAULT_CHAT_MODEL) -> HealthStatus:
    provider = model.split("/")[0]
    key_map = {
        "gemini": ("Google", GOOGLE_API_KEY),
        "openai": ("OpenAI", OPENAI_API_KEY),
        "anthropic": ("Anthropic", ANTHROPIC_API_KEY),
        "zhipuai": ("ZhipuAI", ZHIPUAI_API_KEY),
    }
    name, key = key_map.get(provider, (provider, None))
    if not key:
        return HealthStatus(f"LLM ({name})", False, f"Missing {name} API key")

    try:
        llm = get_llm(model)
        llm.complete("Say 'ok'")
        return HealthStatus(f"LLM ({name})", True, "API key valid")
    except Exception as e:
        return HealthStatus(f"LLM ({name})", False, str(e)[:100])


def check_embedding(model: str = DEFAULT_EMBEDDING_MODEL) -> HealthStatus:
    provider = model.split("/")[0]
    key_map = {
        "gemini": ("Google", GOOGLE_API_KEY),
        "openai": ("OpenAI", OPENAI_API_KEY),
    }
    name, key = key_map.get(provider, ("HuggingFace (local)", None))

    if provider == "huggingface":
        try:
            embed = get_embed_model(model)
            embed.get_text_embedding("test")
            return HealthStatus("Embedding (HuggingFace)", True, "Model loaded")
        except Exception as e:
            return HealthStatus("Embedding (HuggingFace)", False, str(e)[:100])

    if not key:
        return HealthStatus(f"Embedding ({name})", False, f"Missing {name} API key")

    try:
        embed = get_embed_model(model)
        embed.get_text_embedding("test")
        return HealthStatus(f"Embedding ({name})", True, "API key valid")
    except Exception as e:
        return HealthStatus(f"Embedding ({name})", False, str(e)[:100])


def check_all(
    llm_model: str = DEFAULT_CHAT_MODEL, embed_model: str = DEFAULT_EMBEDDING_MODEL
) -> list[HealthStatus]:
    return [
        check_neo4j(),
        check_llm(llm_model),
        check_embedding(embed_model),
    ]
