"""Step B: LLM-based extraction of Topics and Sub-Topics from curriculum text."""

import hashlib
import json
import logging
import time
from collections.abc import Callable
from pathlib import Path

from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.program import LLMTextCompletionProgram
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from src.config import DEFAULT_CHAT_MODEL
from src.filters import filter_text, filter_chunks, FilterResult
from src.llama_setup import get_llm
from src.prompts import get_prompt
from src.schemas import TopicExtraction

CACHE_DIR = Path("data/cache")

logger = logging.getLogger(__name__)

# Default prompt version (used when no prompt_name specified)
DEFAULT_PROMPT_NAME = "default"


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


def _cache_key(text: str, model: str, prompt_version: str) -> str:
    """Return SHA-256 hash of text + model + prompt version for cache keying."""
    return hashlib.sha256((text + model + prompt_version).encode()).hexdigest()


def _chunk_text(text: str) -> list[str]:
    """Split text into token-aware chunks using SentenceSplitter."""
    splitter = SentenceSplitter(chunk_size=2048, chunk_overlap=128)
    return splitter.split_text(text)


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
def _extract_from_chunk(llm, chunk: str, system_prompt: str) -> dict:
    """Use LLMTextCompletionProgram to extract structured topics from a chunk."""
    program = LLMTextCompletionProgram.from_defaults(
        llm=llm,
        output_cls=TopicExtraction,
        prompt_template_str=system_prompt + "\n\nText:\n{text}",
    )
    result: TopicExtraction = program(text=chunk)
    return result.model_dump()


def extract_topics(
    text: str,
    model: str | None = None,
    use_cache: bool = True,
    progress_callback: Callable[[int, int, str], None] | None = None,
    prompt_name: str = "default",
    filter_content: bool = True,
) -> tuple[dict, bool, FilterResult | None]:
    """Extract topics from text.

    Args:
        text: Raw curriculum text
        model: LLM model string
        use_cache: Whether to use cached results
        progress_callback: Optional callback(current, total, message) for progress updates
        prompt_name: Name of the prompt to use from the registry
        filter_content: Whether to filter administrative content before extraction

    Returns:
        (result_dict, from_cache, filter_result)
    """
    model = model or DEFAULT_CHAT_MODEL
    prompt = get_prompt(prompt_name)
    prompt_version = prompt.version

    # Apply text filtering if enabled
    filter_result: FilterResult | None = None
    if filter_content:
        filter_result = filter_text(text)
        text = filter_result.text
        logger.info(
            "Filtered text: %d -> %d chars (%.1f%% reduction)",
            filter_result.original_length,
            filter_result.filtered_length,
            filter_result.reduction_percent,
        )

    cache_file = CACHE_DIR / f"{_cache_key(text, model, prompt_version)}.json"

    if use_cache and cache_file.exists():
        logger.info("Loading cached extraction result from %s", cache_file)
        if progress_callback:
            progress_callback(1, 1, "Loading from cache")
        return json.loads(cache_file.read_text(encoding="utf-8")), True, filter_result

    chunks = _chunk_text(text)

    # Apply chunk filtering if content filtering is enabled
    skipped_chunks: list[str] = []
    if filter_content:
        chunks, skipped_chunks = filter_chunks(chunks)
        if skipped_chunks:
            logger.info("Skipped %d administrative chunks", len(skipped_chunks))

    total_chunks = len(chunks)

    if progress_callback:
        progress_callback(0, total_chunks, "Preparing chunks...")

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    base_hash = _cache_key(text, model, prompt_version)
    all_topics: list[dict] = []
    llm = get_llm(model)

    completed = 0
    for i, chunk in enumerate(chunks):
        chunk_file = CACHE_DIR / f"{base_hash}_chunk{i}.json"
        if chunk_file.exists():
            logger.info("Loaded cached chunk %d/%d", i + 1, total_chunks)
            if progress_callback:
                progress_callback(
                    i + 1, total_chunks, f"Loading chunk {i + 1} from cache"
                )
            parsed = json.loads(chunk_file.read_text(encoding="utf-8"))
        else:
            if completed > 0:
                time.sleep(5)
            if progress_callback:
                progress_callback(
                    i + 1, total_chunks, f"Extracting chunk {i + 1} with LLM..."
                )
            try:
                parsed = _extract_from_chunk(llm, chunk, prompt.system_prompt)
            except Exception:
                if all_topics:
                    logger.warning(
                        "Failed after %d/%d chunks. Re-run later to continue.",
                        i,
                        total_chunks,
                    )
                    result = {
                        "topics": _merge_topics(all_topics),
                        "_partial": True,
                        "_completed_chunks": i,
                        "_total_chunks": total_chunks,
                    }
                    return result, False, filter_result
                raise
            chunk_file.write_text(
                json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            logger.info("Cached chunk %d/%d", i + 1, total_chunks)
            completed += 1
        all_topics.extend(parsed.get("topics", []))

    if progress_callback:
        progress_callback(total_chunks, total_chunks, "Merging topics...")

    result = {"topics": _merge_topics(all_topics)}

    cache_file.write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info("Cached final extraction result to %s", cache_file)

    return result, False, filter_result
