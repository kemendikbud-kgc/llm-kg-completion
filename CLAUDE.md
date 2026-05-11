# AGENTS.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Undergraduate thesis: LLM-Assisted Knowledge Graph Completion for Curriculum Analysis. A Streamlit app that extracts topics from Indonesian curriculum PDFs using LLMs, stores them in Neo4j, and discovers missing relationships via embedding similarity.

## Commands

```bash
# Run the app
streamlit run app.py

# Install dependencies (uses uv, not pip)
uv pip install -e .

# Lint
ruff check src/ app.py
ruff format src/ app.py
```

No test suite exists yet.

## Architecture

Five-step pipeline, each step in its own module under `src/`:

1. **`ingestion.py`** — PDF → raw text (PyPDF2)
2. **`extraction.py`** — Text → structured topics JSON. Chunks text with LlamaIndex `SentenceSplitter`, then uses `LLMTextCompletionProgram` to get validated Pydantic output (`TopicExtraction` from `schemas.py`). Per-chunk disk caching in `data/cache/` with SHA-256 keys. Handles partial extraction on rate limits.
3. **`graph.py`** — Pushes topics/sub-topics to Neo4j as `(:Topic)-[:INCLUDES]->(:SubTopic)` nodes
4. **`completion.py`** — Embeds node descriptions via `LiteLLMEmbedding`, finds similar pairs above a cosine threshold, creates `[:SIMILAR_TO]` edges

Supporting modules:
- **`schemas.py`** — Pydantic models: `TopicExtraction`, `Topic`, `SubTopic`
- **`llama_setup.py`** — Factory functions `get_llm()` / `get_embed_model()` wrapping litellm with LlamaIndex
- **`config.py`** — Env vars, model registries (`MODEL_CHOICES`, `EMBEDDING_CHOICES`), defaults

## Key Patterns

- **litellm as universal backend**: All LLM/embedding calls go through litellm. Model strings use `provider/model` format (e.g. `gemini/gemini-2.5-flash`, `openai/gpt-4o-mini`). LlamaIndex's litellm integrations wrap this.
- **Disk caching**: Extraction results cached as JSON in `data/cache/`. Cache key = SHA-256 of (chunk_text + model). Chunk files: `{hash}_chunk{i}.json`. Final merged result: `{hash}.json`.
- **Pydantic structured output**: `LLMTextCompletionProgram` enforces `TopicExtraction` schema on LLM output — no regex/JSON parsing needed.
- **Multi-provider**: Models configurable via sidebar. Add new models by adding entries to `MODEL_CHOICES` or `EMBEDDING_CHOICES` in `config.py`.

## Environment

Requires `.env` with: `GOOGLE_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`. See `.env.example`.

## Google Workspace References

Thesis artifacts live in Google Drive. Use the `gws` CLI (see `.claude/skills/gws-*`) to read/write.

- **Drive folder** (TA project root): `16WWv6zDdTuxqgxMchGm0RarR2lnTpY_D`
  - URL: https://drive.google.com/drive/u/0/folders/16WWv6zDdTuxqgxMchGm0RarR2lnTpY_D
- **Thesis Doc** (Bab 1–5 draft): `1NUFWP1JHmpH-c_glTlm4t6fzcwJjqAM1BmGS1BzeSGM`
  - Fetch: `gws docs documents get --params '{"documentId":"1NUFWP1JHmpH-c_glTlm4t6fzcwJjqAM1BmGS1BzeSGM"}' --format json`
  - Local cache (gitignored): `.thesis-clean.json` / `.thesis-verify.json`
  - Edits use `batchUpdate` with `writeControl.requiredRevisionId` to prevent collision with concurrent edits in the browser.
