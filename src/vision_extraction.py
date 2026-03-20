"""Vision-based extraction: extract Konsep/SubKonsep from PDF page images via vision LLM."""

import json
import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed

import litellm

from src.cache import cache_manager
from src.config import DEFAULT_VISION_MODEL, VISION_CONCURRENCY

logger = logging.getLogger(__name__)

VISION_SYSTEM_PROMPT = """\
Anda adalah ahli kurikulum pendidikan yang mengekstrak konten dari halaman buku teks Indonesia.

## TUGAS
Analisis gambar halaman buku teks ini dan ekstrak semua konsep yang diajarkan.
Perhatikan dengan seksama:
- **Rumus dan persamaan matematika** (tuliskan dalam notasi teks, misal: F = m × a)
- **Diagram dan gambar** (deskripsikan apa yang ditunjukkan)
- **Tabel** (ekstrak informasi kunci dari tabel)
- **Teks** (ekstrak konsep dan sub-konsep seperti biasa)

## FORMAT OUTPUT (JSON)

```json
{
  "bab_name": "Nama bab jika terdeteksi, null jika tidak",
  "konsep": [
    {
      "name": "Nama Konsep",
      "description": "Deskripsi 1-3 kalimat tentang apa yang diajarkan",
      "sub_konsep": [
        {
          "name": "Nama SubKonsep",
          "description": "Deskripsi detail"
        }
      ]
    }
  ]
}
```

## ATURAN
1. Setiap Konsep HARUS memiliki minimal satu SubKonsep
2. Tulis deskripsi yang menjelaskan APA yang diajarkan
3. Gunakan bahasa yang sama dengan teks sumber
4. Untuk rumus: sertakan rumus dalam deskripsi (misal: "Hukum Newton II menyatakan F = m × a")
5. Untuk diagram: deskripsikan konsep yang ditunjukkan diagram
6. Abaikan nomor halaman, header, footer
7. Output HANYA JSON, tanpa teks tambahan"""


def _parse_vision_response(text: str) -> dict:
    """Parse LLM response, stripping markdown code fences if present."""
    text = text.strip()
    # Strip markdown code fences
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```json or ```)
        lines = lines[1:]
        # Remove last line (```)
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return json.loads(text)


def _extract_single_image(
    page_index: int,
    img_b64: str,
    model: str,
    cache_key: str | None,
) -> tuple[int, dict]:
    """Extract konsep from a single image. Returns (page_index, result)."""
    # Check cache
    if cache_key:
        cached = cache_manager.get_chunk(cache_key, page_index)
        if cached is not None:
            logger.info("Loaded cached vision chunk %d", page_index + 1)
            return page_index, cached

    try:
        response = litellm.completion(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": VISION_SYSTEM_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{img_b64}",
                            },
                        },
                    ],
                }
            ],
            temperature=0.1,
        )
        raw_text = response.choices[0].message.content
        parsed = _parse_vision_response(raw_text)
    except json.JSONDecodeError:
        logger.warning(
            "Failed to parse vision response for page %d, skipping", page_index + 1
        )
        parsed = {"bab_name": None, "konsep": []}
    except Exception:
        logger.warning(
            "Vision extraction failed for page %d, skipping",
            page_index + 1,
            exc_info=True,
        )
        parsed = {"bab_name": None, "konsep": []}

    # Cache the result
    if cache_key:
        cache_manager.put_chunk(cache_key, page_index, parsed)
        logger.info("Cached vision chunk %d", page_index + 1)

    return page_index, parsed


def extract_from_images(
    images_b64: list[str],
    model: str | None = None,
    cache_key: str | None = None,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> list[dict]:
    """Extract konsep from page images using a vision LLM (concurrent).

    Args:
        images_b64: List of base64-encoded PNG images (one per page)
        model: Vision model string (litellm format)
        cache_key: Base hash for per-page caching (if None, no caching)
        progress_callback: Optional callback(current, total, message)

    Returns:
        List of chunk dicts, each with keys: bab_name, konsep
    """
    model = model or DEFAULT_VISION_MODEL
    total = len(images_b64)

    if progress_callback:
        progress_callback(0, total, "Preparing vision extraction...")

    # Check cache for all pages first (fast sequential pass)
    cached_pages = {}
    pages_to_extract = []

    for i, img_b64 in enumerate(images_b64):
        if cache_key:
            cached = cache_manager.get_chunk(cache_key, i)
            if cached is not None:
                cached_pages[i] = cached
                logger.info("Cached: page %d", i + 1)
                continue
        pages_to_extract.append((i, img_b64))

    # Progress for cached pages
    if cached_pages and progress_callback:
        progress_callback(
            len(cached_pages),
            total,
            f"Loaded {len(cached_pages)} pages from cache",
        )

    # Extract uncached pages concurrently
    all_chunks: dict[int, dict] = cached_pages.copy()

    if pages_to_extract:
        with ThreadPoolExecutor(max_workers=VISION_CONCURRENCY) as executor:
            futures = {
                executor.submit(
                    _extract_single_image,
                    idx,
                    img_b64,
                    model,
                    cache_key,
                ): idx
                for idx, img_b64 in pages_to_extract
            }

            completed_count = len(cached_pages)
            for future in as_completed(futures):
                page_idx, result = future.result()
                all_chunks[page_idx] = result
                completed_count += 1
                if progress_callback:
                    progress_callback(
                        completed_count,
                        total,
                        f"Extracted page {page_idx + 1} ({completed_count}/{total})",
                    )
                logger.info(
                    "Completed: page %d (%d/%d)", page_idx + 1, completed_count, total
                )

    # Return in original order
    return [all_chunks[i] for i in range(total)]
