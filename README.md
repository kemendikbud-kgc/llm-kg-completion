# LLM-Assisted Knowledge Graph Completion

Undergraduate thesis project: LLM-Assisted Knowledge Graph Completion for Curriculum Analysis.

## Stack

- **Python** + **Streamlit** (UI & logic)
- **Neo4j Aura** (graph database)
- **LangChain** + **OpenAI GPT-4o** (LLM extraction)
- **scikit-learn** (semantic similarity for KG completion)

## Setup

```bash
pip install -e .
cp .env.example .env
# Fill in your API keys in .env
```

## Run

```bash
streamlit run app.py
```

## Pipeline

1. **Ingestion** - Upload PDF (Capaian Pembelajaran) → extract text
2. **Extraction** - LLM extracts Topics/Sub-Topics as structured JSON
3. **Validation** - Human-in-the-loop review and edit
4. **Construction** - Push validated data to Neo4j
5. **Completion** - Semantic similarity to discover missing relationships
