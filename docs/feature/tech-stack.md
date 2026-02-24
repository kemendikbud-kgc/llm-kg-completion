# Tech Stack

## Core Pipeline

| Layer | Technology | Role |
|-------|-----------|------|
| **UI** | Streamlit | Interactive web app for the pipeline workflow |
| **LLM Backend** | litellm | Multi-provider LLM router (Google, OpenAI, Anthropic, ZhipuAI) |
| **Structured Extraction** | LlamaIndex + Pydantic | Token-aware chunking (`SentenceSplitter`), validated JSON output (`LLMTextCompletionProgram`) |
| **Embeddings** | LlamaIndex `LiteLLMEmbedding` | Batch embedding + cosine similarity for KG completion |
| **Knowledge Graph** | Neo4j | Graph storage for topics, sub-topics, and similarity relationships |
| **PDF Ingestion** | PyPDF2 | Text extraction from curriculum PDFs |

## Why LlamaIndex over raw litellm calls

1. **Structured output** — `LLMTextCompletionProgram` returns validated Pydantic models instead of raw JSON strings that need regex stripping and manual parsing.
2. **Token-aware chunking** — `SentenceSplitter` respects sentence boundaries and counts tokens, replacing the naive character-based chunker.
3. **Embedding abstraction** — `LiteLLMEmbedding` handles batching internally and provides a `similarity()` function, removing the numpy/scikit-learn dependency.
4. **litellm stays** — LlamaIndex's litellm integrations (`llama-index-llms-litellm`, `llama-index-embeddings-litellm`) use litellm under the hood, preserving multi-provider support.

## Key Design Decisions

- **Disk caching** — Extraction results are cached per-chunk as JSON files in `data/cache/`. This survives rate limits and allows resuming partial extractions.
- **No LangChain** — Removed in favor of LlamaIndex which provides tighter Pydantic integration for structured extraction.
- **Pydantic schemas** — `src/schemas.py` defines `TopicExtraction`, `Topic`, and `SubTopic` models used both for LLM output validation and as a data contract.
