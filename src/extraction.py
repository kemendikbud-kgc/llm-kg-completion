"""Step B: LLM-based extraction of Konsep and SubKonsep from curriculum text."""

import logging
import time
from collections.abc import Callable

from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.program import LLMTextCompletionProgram
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from src.cache import cache_manager
from src.config import DEFAULT_CHAT_MODEL, DEFAULT_VISION_MODEL
from src.filters import filter_text, filter_chunks, FilterResult
from src.llama_setup import get_llm
from src.prompts import get_prompt
from src.schemas import TopicExtraction

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


def _merge_konsep(all_chunks_data: list[dict]) -> dict:
    """Deduplicate konsep by name across chunks, merging sub_konsep.

    Each chunk dict has keys: bab_name (str|None), sub_bab_name (str|None),
    sub_sub_bab_name (str|None), konsep (list[dict]).
    Returns {"konsep": [...]} where each konsep has "bab", "sub_bab", and "sub_sub_bab" fields.
    """
    merged: dict[str, dict] = {}
    for chunk in all_chunks_data:
        bab_name = chunk.get("bab_name")
        sub_bab_name = chunk.get("sub_bab_name")
        sub_sub_bab_name = chunk.get("sub_sub_bab_name")
        for konsep in chunk.get("konsep", []):
            name = konsep["name"]
            if name not in merged:
                merged[name] = {
                    **konsep,
                    "bab": bab_name,
                    "sub_bab": sub_bab_name,
                    "sub_sub_bab": sub_sub_bab_name,
                    "sub_konsep": list(konsep.get("sub_konsep", [])),
                }
            else:
                existing_sub_names = {
                    s["name"] for s in merged[name].get("sub_konsep", [])
                }
                for sub in konsep.get("sub_konsep", []):
                    if sub["name"] not in existing_sub_names:
                        merged[name]["sub_konsep"].append(sub)
                        existing_sub_names.add(sub["name"])
    return {"konsep": list(merged.values())}


# Keep backward-compat name
def _merge_topics(all_topics: list[dict]) -> list[dict]:
    """Legacy: deduplicate topics by name, merging sub-topics. Returns list."""
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


def _chunk_text(text: str) -> list[str]:
    """Split text into token-aware chunks using SentenceSplitter."""
    splitter = SentenceSplitter(chunk_size=2048, chunk_overlap=128)
    return splitter.split_text(text)


def _chunk_pages(
    pages: list[tuple[int, str]],
) -> list[tuple[str, int]]:
    """Split page-aware text into chunks, preserving the starting page number.

    Returns list of (chunk_text, page_num) tuples where page_num is the
    1-based page number of the first page contributing to that chunk.
    """
    splitter = SentenceSplitter(chunk_size=2048, chunk_overlap=128)
    result: list[tuple[str, int]] = []
    for page_num, page_text in pages:
        if not page_text.strip():
            continue
        chunks = splitter.split_text(page_text)
        for chunk in chunks:
            result.append((chunk, page_num))
    return result


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
    """Use LLMTextCompletionProgram to extract structured konsep from a chunk."""
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
    document_name: str | None = None,
    doc_structure=None,  # DocumentStructure | None — avoids circular import
    pages: list[tuple[int, str]] | None = None,
    glossary: dict[str, str] | None = None,
) -> tuple[dict, bool, FilterResult | None]:
    """Extract konsep from text.

    Args:
        text: Raw curriculum text
        model: LLM model string
        use_cache: Whether to use cached results
        progress_callback: Optional callback(current, total, message) for progress updates
        prompt_name: Name of the prompt to use from the registry
        filter_content: Whether to filter administrative content before extraction

    Returns:
        (result_dict, from_cache, filter_result)
        result_dict has key "konsep": list of konsep dicts (each with optional "bab" field)
    """
    model = model or DEFAULT_CHAT_MODEL
    prompt = get_prompt(prompt_name)
    prompt_version = prompt.version

    # Build system prompt, optionally enriched with glossary context
    from src.prompts import build_glossary_context

    system_prompt = prompt.system_prompt
    if glossary:
        system_prompt = system_prompt + build_glossary_context(glossary)

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

    if use_cache:
        cached = cache_manager.get_extraction(text, model, prompt_version)
        if cached is not None:
            logger.info("Loading cached extraction result")
            if progress_callback:
                progress_callback(1, 1, "Loading from cache")
            cached = _normalize_result(cached)
            return cached, True, filter_result

    # Build page-aware chunks if pages + structure provided; fall back to plain text
    from src.ingestion import get_structure_for_page

    if pages and doc_structure and doc_structure.found:
        chunks_with_pages: list[tuple[str, int]] = _chunk_pages(pages)
    else:
        chunks_with_pages = [(_c, 0) for _c in _chunk_text(text)]

    # Apply chunk filtering if content filtering is enabled
    if filter_content:
        plain_chunks = [c for c, _ in chunks_with_pages]
        filtered_plain, skipped_chunks = filter_chunks(plain_chunks)
        filtered_set = set(filtered_plain)
        chunks_with_pages = [(c, p) for c, p in chunks_with_pages if c in filtered_set]
        if skipped_chunks:
            logger.info("Skipped %d administrative chunks", len(skipped_chunks))

    total_chunks = len(chunks_with_pages)

    if progress_callback:
        progress_callback(0, total_chunks, "Preparing chunks...")

    base_hash = cache_manager.get_extraction_hash(text, model, prompt_version)
    all_chunks_data: list[dict] = []
    llm = get_llm(model)

    completed = 0
    for i, (chunk, page_num) in enumerate(chunks_with_pages):
        cached_chunk = cache_manager.get_chunk(base_hash, i)
        if cached_chunk is not None:
            logger.info("Loaded cached chunk %d/%d", i + 1, total_chunks)
            if progress_callback:
                progress_callback(
                    i + 1, total_chunks, f"Loading chunk {i + 1} from cache"
                )
            parsed = cached_chunk
        else:
            if completed > 0:
                time.sleep(5)
            if progress_callback:
                progress_callback(
                    i + 1, total_chunks, f"Extracting chunk {i + 1} with LLM..."
                )
            try:
                parsed = _extract_from_chunk(llm, chunk, system_prompt)
            except Exception:
                if all_chunks_data:
                    partial_konsep = _merge_konsep(all_chunks_data)["konsep"]
                    logger.warning(
                        "Failed after %d/%d chunks. Re-run later to continue.",
                        i,
                        total_chunks,
                    )
                    result = {
                        "konsep": partial_konsep,
                        "_partial": True,
                        "_completed_chunks": i,
                        "_total_chunks": total_chunks,
                    }
                    return result, False, filter_result
                raise
            cache_manager.put_chunk(base_hash, i, parsed)
            logger.info("Cached chunk %d/%d", i + 1, total_chunks)
            completed += 1

        # Normalize old chunk format (topics -> konsep) for backward compat
        parsed = _normalize_chunk(parsed)

        # Stamp bab/sub_bab/sub_sub_bab from ToC structure if available, else use LLM-detected bab_name
        if doc_structure and doc_structure.found and page_num > 0:
            stamped_bab, stamped_sub_bab, stamped_sub_sub_bab = get_structure_for_page(
                doc_structure, page_num
            )
        else:
            stamped_bab = parsed.get("bab_name")
            stamped_sub_bab = None
            stamped_sub_sub_bab = None

        all_chunks_data.append(
            {
                "bab_name": stamped_bab,
                "sub_bab_name": stamped_sub_bab,
                "sub_sub_bab_name": stamped_sub_sub_bab,
                "konsep": parsed.get("konsep", []),
            }
        )

    if progress_callback:
        progress_callback(total_chunks, total_chunks, "Merging konsep...")

    result = _merge_konsep(all_chunks_data)

    cache_manager.put_extraction(
        text, model, prompt_version, result, document_name=document_name
    )

    return result, False, filter_result


def extract_topics_hybrid(
    text: str,
    vision_images: list[str],
    text_model: str | None = None,
    vision_model: str | None = None,
    use_cache: bool = True,
    progress_callback: Callable[[int, int, str], None] | None = None,
    prompt_name: str = "default",
    filter_content: bool = True,
    document_name: str | None = None,
) -> tuple[dict, bool, FilterResult | None]:
    """Hybrid extraction: text extraction + vision extraction, merged.

    Args:
        text: Raw text from text-classified pages
        vision_images: Base64 PNGs from vision-classified pages
        text_model: LLM model for text extraction
        vision_model: Vision model for image extraction
        use_cache: Whether to use cached results
        progress_callback: Optional callback(current, total, message)
        prompt_name: Prompt name for text extraction
        filter_content: Whether to filter administrative content
        document_name: Document name for cache metadata

    Returns:
        (result_dict, from_cache, filter_result) — same format as extract_topics()
    """
    from src.vision_extraction import extract_from_images

    vision_model = vision_model or DEFAULT_VISION_MODEL
    text_model = text_model or DEFAULT_CHAT_MODEL

    # Run text extraction if there's text content
    text_result: dict = {"konsep": []}
    text_from_cache = False
    filter_result: FilterResult | None = None

    if text.strip():
        text_result, text_from_cache, filter_result = extract_topics(
            text,
            model=text_model,
            use_cache=use_cache,
            progress_callback=progress_callback,
            prompt_name=prompt_name,
            filter_content=filter_content,
            document_name=document_name,
        )

    # Run vision extraction if there are images
    vision_chunks: list[dict] = []
    if vision_images:
        # Generate cache key for vision extraction
        prompt = get_prompt(prompt_name)
        vision_cache_key = None
        if use_cache:
            import hashlib

            # Cache key based on image count + vision model + prompt version
            vision_hash_input = (
                f"vision_{len(vision_images)}_{vision_model}_{prompt.version}"
            )
            if document_name:
                vision_hash_input += f"_{document_name}"
            vision_cache_key = hashlib.sha256(vision_hash_input.encode()).hexdigest()

        if progress_callback:
            progress_callback(0, len(vision_images), "Starting vision extraction...")

        vision_chunks = extract_from_images(
            vision_images,
            model=vision_model,
            cache_key=vision_cache_key,
            progress_callback=progress_callback,
        )

    # Merge text and vision results
    if vision_chunks:
        all_chunks = []
        # Add text konsep as a chunk
        if text_result.get("konsep"):
            all_chunks.append({"bab_name": None, "konsep": text_result["konsep"]})
        # Add vision chunks
        for chunk in vision_chunks:
            all_chunks.append(
                {
                    "bab_name": chunk.get("bab_name"),
                    "konsep": chunk.get("konsep", []),
                }
            )
        merged = _merge_konsep(all_chunks)
        return merged, text_from_cache, filter_result

    return text_result, text_from_cache, filter_result


def extract_topics_per_subbab(
    pages: list[tuple[int, str]],
    doc_structure,  # DocumentStructure — avoids circular import
    glossary: dict[str, str] | None = None,
    model: str | None = None,
    use_cache: bool = True,
    progress_callback: Callable[[int, int, str], None] | None = None,
    prompt_name: str = "default",
    filter_content: bool = True,
    document_name: str | None = None,
) -> dict:
    """Extract konsep per SubBab/SubSubBab using ToC-scoped text sections.

    Iterates over unique (bab, sub_bab, sub_sub_bab) triples from ``doc_structure``,
    slices ``pages`` to the section's page range, and calls :func:`extract_topics`
    with that scoped text and optional glossary context.

    Returns a merged ``{"konsep": [...]}`` dict where each konsep is already
    tagged with the correct ``bab``, ``sub_bab``, and ``sub_sub_bab``.
    """
    from src.ingestion import extract_pages_for_subbab

    # Collect unique (bab, sub_bab, sub_sub_bab) triples in ToC order
    seen_set: set[tuple[str, str | None, str | None]] = set()
    sections: list[tuple[str, str | None, str | None]] = []
    for entry in doc_structure.entries:
        key = (entry.bab, entry.sub_bab, entry.sub_sub_bab)
        if key not in seen_set:
            seen_set.add(key)
            sections.append(key)

    total = len(sections)
    all_konsep: list[dict] = []

    for i, (bab_name, sub_bab_name, sub_sub_bab_name) in enumerate(sections):
        section_text = extract_pages_for_subbab(
            pages, doc_structure, bab_name, sub_bab_name, sub_sub_bab_name
        )
        if not section_text.strip():
            continue

        # Build label for progress display
        parts = [bab_name]
        if sub_bab_name:
            parts.append(sub_bab_name)
        if sub_sub_bab_name:
            parts.append(sub_sub_bab_name)
        label = " / ".join(parts)

        if progress_callback:
            progress_callback(i, total, f"Extracting: {label}")

        section_result, _, _ = extract_topics(
            section_text,
            model=model,
            use_cache=use_cache,
            prompt_name=prompt_name,
            filter_content=filter_content,
            document_name=document_name,
            glossary=glossary,
        )

        for k in section_result.get("konsep", []):
            k["bab"] = bab_name
            k["sub_bab"] = sub_bab_name
            k["sub_sub_bab"] = sub_sub_bab_name
            all_konsep.append(k)

    if progress_callback:
        progress_callback(total, total, "Merging konsep...")

    # Deduplicate by name, keeping first bab/sub_bab/sub_sub_bab and merging sub_konsep
    merged: dict[str, dict] = {}
    for k in all_konsep:
        name = k["name"]
        if name not in merged:
            merged[name] = {**k, "sub_konsep": list(k.get("sub_konsep", []))}
        else:
            existing_subs = {s["name"] for s in merged[name].get("sub_konsep", [])}
            for sub in k.get("sub_konsep", []):
                if sub["name"] not in existing_subs:
                    merged[name]["sub_konsep"].append(sub)
                    existing_subs.add(sub["name"])

    return {"konsep": list(merged.values())}


def _normalize_chunk(parsed: dict) -> dict:
    """Normalize old chunk format (topics/sub_topics) to new (konsep/sub_konsep)."""
    if "topics" in parsed and "konsep" not in parsed:
        konsep = []
        for t in parsed.get("topics", []):
            sub_konsep = [
                {
                    "name": s["name"],
                    "description": s.get("description", ""),
                    "bloom_level": None,
                }
                for s in t.get("sub_topics", [])
            ]
            konsep.append(
                {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "bloom_level": None,
                    "sub_konsep": sub_konsep,
                }
            )
        return {"bab_name": None, "konsep": konsep}
    return parsed


def _normalize_result(result: dict) -> dict:
    """Normalize old result format (topics) to new (konsep)."""
    if "topics" in result and "konsep" not in result:
        konsep = []
        for t in result.get("topics", []):
            sub_konsep = [
                {
                    "name": s["name"],
                    "description": s.get("description", ""),
                    "bloom_level": None,
                }
                for s in t.get("sub_topics", [])
            ]
            konsep.append(
                {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "bloom_level": None,
                    "bab": None,
                    "sub_bab": None,
                    "sub_konsep": sub_konsep,
                }
            )
        return {**result, "konsep": konsep}
    return result
