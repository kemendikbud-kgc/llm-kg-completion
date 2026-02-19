"""Step B: LLM-based extraction of Topics and Sub-Topics from curriculum text."""

import hashlib
import json
import time
import logging
from pathlib import Path

from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.program import LLMTextCompletionProgram

from src.config import DEFAULT_CHAT_MODEL
from src.llama_setup import get_llm
from src.schemas import TopicExtraction

CACHE_DIR = Path("data/cache")

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are an expert curriculum designer. I will give you a text from a science curriculum.

Definitions:
- Topic: An abstract concept taught in a session.
- Sub-Topic: Fine-grained content explained in detail.

Task: Extract all Topics and Sub-Topics from the text below.
Output strictly in JSON format matching the schema."""


def _merge_topics(all_topics: list[dict]) -> list[dict]:
    """Deduplicate topics by name, merging sub-topics."""
    merged = {}
    for topic in all_topics:
        name = topic["name"]
        if name not in merged:
            merged[name] = {**topic, "sub_topics": list(topic.get("sub_topics", []))}
        else:
            existing_sub_names = {s["name"] for s in merged[name].get("sub_topics", [])}
            for sub in topic.get("sub_topics", []):
                if sub["name"] not in existing_sub_names:
                    merged[name]["sub_topics"].append(sub)
                    existing_sub_names.add(sub["name"])
    return list(merged.values())


def _cache_key(text: str, model: str) -> str:
    """Return SHA-256 hash of text + model for cache keying."""
    return hashlib.sha256((text + model).encode()).hexdigest()


def _chunk_text(text: str) -> list[str]:
    """Split text into token-aware chunks using SentenceSplitter."""
    splitter = SentenceSplitter(chunk_size=2048, chunk_overlap=128)
    return splitter.split_text(text)


def _extract_from_chunk(llm, chunk: str) -> dict:
    """Use LLMTextCompletionProgram to extract structured topics from a chunk."""
    program = LLMTextCompletionProgram.from_defaults(
        llm=llm,
        output_cls=TopicExtraction,
        prompt_template_str=SYSTEM_PROMPT + "\n\nText:\n{text}",
    )
    result: TopicExtraction = program(text=chunk)
    return result.model_dump()


def extract_topics(text: str, model: str | None = None, use_cache: bool = True) -> tuple[dict, bool]:
    """Extract topics from text. Returns (result_dict, from_cache)."""
    model = model or DEFAULT_CHAT_MODEL

    cache_file = CACHE_DIR / f"{_cache_key(text, model)}.json"

    if use_cache and cache_file.exists():
        logger.info("Loading cached extraction result from %s", cache_file)
        return json.loads(cache_file.read_text(encoding="utf-8")), True

    chunks = _chunk_text(text)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    base_hash = _cache_key(text, model)
    all_topics: list[dict] = []
    llm = get_llm(model)

    completed = 0
    for i, chunk in enumerate(chunks):
        chunk_file = CACHE_DIR / f"{base_hash}_chunk{i}.json"
        if chunk_file.exists():
            logger.info("Loaded cached chunk %d/%d", i + 1, len(chunks))
            parsed = json.loads(chunk_file.read_text(encoding="utf-8"))
        else:
            if completed > 0:
                time.sleep(5)
            try:
                parsed = _extract_from_chunk(llm, chunk)
            except Exception:
                if all_topics:
                    logger.warning(
                        "Failed after %d/%d chunks. Re-run later to continue.",
                        i, len(chunks),
                    )
                    result = {"topics": _merge_topics(all_topics), "_partial": True,
                              "_completed_chunks": i, "_total_chunks": len(chunks)}
                    return result, False
                raise
            chunk_file.write_text(json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8")
            logger.info("Cached chunk %d/%d", i + 1, len(chunks))
            completed += 1
        all_topics.extend(parsed.get("topics", []))

    result = {"topics": _merge_topics(all_topics)}

    cache_file.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Cached final extraction result to %s", cache_file)

    return result, False
