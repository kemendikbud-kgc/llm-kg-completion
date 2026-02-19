"""Step B: LLM-based extraction of Topics and Sub-Topics from curriculum text."""

import json
import re
import time
import logging
import litellm
from src.config import DEFAULT_CHAT_MODEL

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert curriculum designer. I will give you a text from a science curriculum.

Definitions:
- Topic: An abstract concept taught in a session.
- Sub-Topic: Fine-grained content explained in detail.

Task: Extract all Topics and Sub-Topics from the text below.
Output strictly in JSON format:
{
  "topics": [
    {
      "name": "...",
      "description": "...",
      "sub_topics": [
        {"name": "...", "description": "..."}
      ]
    }
  ]
}"""


def chunk_text(text: str, max_chars: int = 12000, overlap: int = 500) -> list[str]:
    """Split text into overlapping chunks."""
    if len(text) <= max_chars:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + max_chars
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


def _strip_code_fences(text: str) -> str:
    """Strip markdown code fences (```json ... ```) from LLM output."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    return text.strip()


def _call_llm_with_retry(model: str, text: str, max_retries: int = 8) -> str:
    """Call LLM with exponential backoff retry."""
    for attempt in range(max_retries):
        try:
            response = litellm.completion(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
                temperature=0.1,
            )
            return response.choices[0].message.content
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            wait = min(5 * (2 ** attempt), 120)
            logger.warning(f"LLM call failed (attempt {attempt + 1}): {e}. Retrying in {wait}s...")
            time.sleep(wait)


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


def extract_topics(text: str, model: str | None = None) -> dict:
    model = model or DEFAULT_CHAT_MODEL

    chunks = chunk_text(text)
    all_topics = []
    for i, chunk in enumerate(chunks):
        if i > 0:
            time.sleep(2)
        raw = _call_llm_with_retry(model, chunk)
        raw = _strip_code_fences(raw)
        parsed = json.loads(raw)
        all_topics.extend(parsed.get("topics", []))

    return {"topics": _merge_topics(all_topics)}
