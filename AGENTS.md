# AGENTS.md

Guidance for coding agents working in this repository.

## Project

Research artifact: LLM-assisted knowledge graph completion over Indonesian Grade XII
science textbooks. See `README.md` for pipeline and layout.

## Commands

```bash
uv pip install -e .                    # install (uv, not pip)
streamlit run pages/5_Completion.py    # completion stage UI
ruff check src/ pages/ && ruff format src/ pages/
```

No test suite exists yet.

## Architecture

- Stages 1-3 (ingest, extract, construct) live in `experiments/yhoga/TA_KG/*.ipynb`
  (Google GenAI SDK, Neo4j `Grade/Chapter/Subtopic/Concept` ontology).
- Stage 4 (completion) lives in `src/`:
  - `completion.py`: embed concepts, ANN retrieve via Neo4j vector index, prune,
    classify pairs with an LLM into `LINTAS_BUKU_*` labels.
  - `schema_adapter.py`: `YhogaAdapter` maps completion onto the paper ontology.
  - `cache.py`: embedding and classification caches (gitignored, under `data/`).
  - `config.py`, `llama_setup.py`: model registry, litellm-backed LlamaIndex models.
- `data/canonical/` is the single source of truth for paper numbers.

## Key patterns

- All LLM/embedding calls go through litellm (`provider/model`, e.g. `gemini/gemini-2.5-flash`).
- Classification cache key includes prompt version and a graph-context fingerprint;
  bump `CLASSIFICATION_PROMPT_VERSION` when the prompt or schema changes.

## Environment

`.env` needs `GOOGLE_API_KEY` and `NEO4J_URI_YHOGA` / `NEO4J_USERNAME_YHOGA` /
`NEO4J_PASSWORD_YHOGA`. See `.env.example`.
