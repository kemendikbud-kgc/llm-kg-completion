"""Streamlit app - main entry point."""

import streamlit as st
import json
from pathlib import Path

from src.ingestion import extract_text_from_pdf
from src.extraction import extract_topics, CACHE_DIR, _merge_topics  # noqa: F401
from src.graph import get_driver, insert_topics, get_all_nodes
from src.completion import find_similar_pairs
from src.config import MODEL_CHOICES, EMBEDDING_CHOICES, DEFAULT_CHAT_MODEL, DEFAULT_EMBEDDING_MODEL

st.set_page_config(page_title="KG Completion Pipeline", layout="wide")
st.title("LLM-Assisted Knowledge Graph Completion")

# --- Sidebar: Model Selection ---
with st.sidebar:
    st.header("Model Settings")

    chat_model_name = st.selectbox(
        "Chat Model",
        options=list(MODEL_CHOICES.keys()),
        index=list(MODEL_CHOICES.values()).index(DEFAULT_CHAT_MODEL),
    )
    selected_chat_model = MODEL_CHOICES[chat_model_name]
    st.caption(f"`{selected_chat_model}`")

    embedding_model_name = st.selectbox(
        "Embedding Model",
        options=list(EMBEDDING_CHOICES.keys()),
        index=list(EMBEDDING_CHOICES.values()).index(DEFAULT_EMBEDDING_MODEL),
    )
    selected_embedding_model = EMBEDDING_CHOICES[embedding_model_name]
    st.caption(f"`{selected_embedding_model}`")

    # --- Load from cache ---
    st.divider()
    st.header("Load Cached Result")
    cache_files = sorted(CACHE_DIR.glob("*.json")) if CACHE_DIR.exists() else []
    # Only show final merged results (no _chunk files)
    cache_files = [f for f in cache_files if "_chunk" not in f.name]
    if cache_files:
        selected_cache = st.selectbox(
            "Cached extractions",
            options=cache_files,
            format_func=lambda f: f.stem[:12] + "...",
        )
        if st.button("Load cached result"):
            data = json.loads(selected_cache.read_text(encoding="utf-8"))
            st.session_state["extracted"] = data
            st.success("Loaded from cache file.")
    else:
        # Collect chunk groups and offer to merge them
        chunk_files = sorted(CACHE_DIR.glob("*_chunk*.json")) if CACHE_DIR.exists() else []
        if chunk_files:
            # Group by base hash
            hashes = sorted(set(f.stem.rsplit("_chunk", 1)[0] for f in chunk_files))
            selected_hash = st.selectbox("Cached chunk groups", options=hashes,
                                         format_func=lambda h: h[:12] + "...")
            group = sorted([f for f in chunk_files if f.stem.startswith(selected_hash)],
                           key=lambda f: int(f.stem.rsplit("_chunk", 1)[1]))
            st.caption(f"{len(group)} chunks cached")
            if st.button("Merge & load chunks"):
                all_topics = []
                for cf in group:
                    parsed = json.loads(cf.read_text(encoding="utf-8"))
                    all_topics.extend(parsed.get("topics", []))
                result = {"topics": _merge_topics(all_topics)}
                st.session_state["extracted"] = result
                st.success(f"Merged {len(group)} chunks.")
        else:
            st.caption("No cached results found.")

# Step 1: Upload PDF
st.header("1. Upload Curriculum Document")
uploaded_file = st.file_uploader("Upload a PDF (Capaian Pembelajaran)", type="pdf")

if uploaded_file:
    import tempfile, os
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name

    raw_text = extract_text_from_pdf(tmp_path)
    os.unlink(tmp_path)

    st.text_area("Extracted Text", raw_text, height=200)

    # Step 2: LLM Extraction
    st.header("2. Extract Topics (LLM)")
    use_cache = st.checkbox("Use cached results (if available)", value=True)
    if st.button("Run Extraction"):
        with st.spinner("Calling LLM..."):
            result, from_cache = extract_topics(raw_text, model=selected_chat_model, use_cache=use_cache)
        st.session_state["extracted"] = result
        if from_cache:
            st.info("Loaded from cache.")
        elif result.get("_partial"):
            st.warning(
                f"Rate limited — extracted {result['_completed_chunks']}/{result['_total_chunks']} chunks. "
                "Cached chunks are saved. Click **Run Extraction** again later to continue."
            )
        else:
            st.success("Fresh LLM extraction complete.")

    # Step 3: Human-in-the-loop validation
    if "extracted" in st.session_state:
        st.header("3. Validate & Edit")
        edited = st.text_area(
            "Edit JSON if needed:",
            json.dumps(st.session_state["extracted"], indent=2),
            height=400,
        )

        # Step 4: Push to Neo4j
        st.header("4. Save to Knowledge Graph")
        if st.button("Save to Neo4j"):
            data = json.loads(edited)
            driver = get_driver()
            insert_topics(driver, data)
            driver.close()
            st.success("Data saved to Neo4j!")
            st.session_state["neo4j_saved"] = True

        # Step 5: Knowledge Graph Completion
        if st.session_state.get("neo4j_saved"):
            st.header("5. Knowledge Graph Completion")
            threshold = st.slider("Similarity threshold", 0.5, 1.0, 0.8, 0.05)
            if st.button("Find Similar Topics"):
                with st.spinner("Computing embeddings..."):
                    driver = get_driver()
                    nodes = get_all_nodes(driver)
                    driver.close()

                    names = [n["name"] for n in nodes if n["name"]]
                    descriptions = names
                    pairs = find_similar_pairs(
                        names, descriptions,
                        threshold=threshold,
                        embedding_model=selected_embedding_model,
                    )

                if pairs:
                    st.success(f"Found {len(pairs)} similar pair(s)!")
                    for p in pairs:
                        st.write(f"**{p['source']}** ↔ **{p['target']}** (similarity: {p['similarity']:.3f})")

                    if st.button("Save relationships to Neo4j"):
                        driver = get_driver()
                        with driver.session() as session:
                            for p in pairs:
                                session.run(
                                    "MATCH (a {name: $src}), (b {name: $tgt}) "
                                    "MERGE (a)-[:SIMILAR_TO {score: $score}]->(b)",
                                    src=p["source"], tgt=p["target"], score=p["similarity"],
                                )
                        driver.close()
                        st.success("Relationships saved!")
                else:
                    st.info("No similar pairs found above the threshold.")
