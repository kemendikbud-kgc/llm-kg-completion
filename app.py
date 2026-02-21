"""Streamlit app - main entry point."""

import json
import logging

import streamlit as st

from src.ingestion import extract_text_from_pdf
from src.extraction import extract_topics, CACHE_DIR, _merge_topics
from src.graph import (
    get_driver,
    insert_topics,
    get_all_documents,
    get_graph_stats,
    get_all_topics_with_subtopics,
    get_similar_relationships,
    get_nodes_with_descriptions,
)
from src.completion import find_similar_pairs
from src.config import (
    MODEL_CHOICES,
    EMBEDDING_CHOICES,
    DEFAULT_CHAT_MODEL,
    DEFAULT_EMBEDDING_MODEL,
)
from src.health import check_all

logger = logging.getLogger(__name__)

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

    st.divider()
    st.header("Load Cached Result")
    cache_files = sorted(CACHE_DIR.glob("*.json")) if CACHE_DIR.exists() else []
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
        chunk_files = (
            sorted(CACHE_DIR.glob("*_chunk*.json")) if CACHE_DIR.exists() else []
        )
        if chunk_files:
            hashes = sorted(set(f.stem.rsplit("_chunk", 1)[0] for f in chunk_files))
            selected_hash = st.selectbox(
                "Cached chunk groups",
                options=hashes,
                format_func=lambda h: h[:12] + "...",
            )
            group = sorted(
                [f for f in chunk_files if f.stem.startswith(selected_hash)],
                key=lambda f: int(f.stem.rsplit("_chunk", 1)[1]),
            )
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

# --- Knowledge Graph Explorer (always visible) ---
with st.expander("🔍 Knowledge Graph Explorer", expanded=True):
    col1, col2, col3, col4 = st.columns(4)

    try:
        driver = get_driver()
        stats = get_graph_stats(driver)
        driver.close()

        col1.metric("Documents", stats["documents"])
        col2.metric("Topics", stats["topics"])
        col3.metric("SubTopics", stats["subtopics"])
        col4.metric("SIMILAR_TO", stats["similar_rels"])

        if st.button("View Graph Details"):
            st.session_state["show_graph_details"] = True

        if st.session_state.get("show_graph_details"):
            st.subheader("Topics Overview")
            driver = get_driver()
            topics = get_all_topics_with_subtopics(driver)
            documents = get_all_documents(driver)
            similar_rels = get_similar_relationships(driver)
            driver.close()

            tab1, tab2, tab3 = st.tabs(["Documents", "Topics", "Similar Relationships"])

            with tab1:
                if documents:
                    for doc in documents:
                        st.write(f"- **{doc['name']}** ({doc['topic_count']} topics)")
                else:
                    st.info("No documents yet.")

            with tab2:
                if topics:
                    for t in topics[:20]:
                        with st.expander(f"**{t['name']}**"):
                            if t.get("description"):
                                st.write(f"*{t['description']}*")
                            subtopics = [
                                s for s in t.get("subtopics", []) if s.get("name")
                            ]
                            if subtopics:
                                st.write("**SubTopics:**")
                                for s in subtopics[:5]:
                                    st.write(f"  - {s['name']}")
                            docs = t.get("documents", [])
                            if docs:
                                st.write(f"**In documents:** {', '.join(docs)}")
                    if len(topics) > 20:
                        st.info(f"Showing 20 of {len(topics)} topics.")
                else:
                    st.info("No topics yet.")

            with tab3:
                if similar_rels:
                    for rel in similar_rels[:20]:
                        st.write(
                            f"**{rel['source']}** ↔ **{rel['target']}** "
                            f"(score: {rel['score']:.3f})"
                        )
                    if len(similar_rels) > 20:
                        st.info(f"Showing 20 of {len(similar_rels)} relationships.")
                else:
                    st.info(
                        "No SIMILAR_TO relationships found. Run Step 5 to discover them."
                    )

    except Exception as e:
        st.error(f"Could not connect to Neo4j: {e}")

# --- Health Check ---
with st.expander("🔧 System Health Check", expanded=False):
    if st.button("Run Health Check"):
        with st.spinner("Checking connections..."):
            results = check_all(DEFAULT_CHAT_MODEL, DEFAULT_EMBEDDING_MODEL)
        for r in results:
            if r.ok:
                st.success(f"✅ {r.service}: {r.message}")
            else:
                st.error(f"❌ {r.service}: {r.message}")

st.divider()

# --- Step 1: Upload PDF ---
st.header("1. Upload Curriculum Document")
uploaded_file = st.file_uploader("Upload a PDF (Capaian Pembelajaran)", type="pdf")

raw_text = None
if uploaded_file:
    import tempfile
    import os

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name

    raw_text = extract_text_from_pdf(tmp_path)
    os.unlink(tmp_path)

    st.session_state["document_name"] = uploaded_file.name
    st.text_area("Extracted Text", raw_text, height=200)

# --- Step 2: LLM Extraction ---
st.header("2. Extract Topics (LLM)")
if raw_text:
    use_cache = st.checkbox("Use cached results (if available)", value=True)
    if st.button("Run Extraction", type="primary"):
        progress_bar = st.progress(0, text="Preparing...")
        status_text = st.empty()

        def update_progress(current: int, total: int, message: str):
            if total > 0:
                progress_bar.progress(
                    current / total, text=f"{message} ({current}/{total})"
                )
            status_text.info(message)
            logger.info("[Step 2] %s (%d/%d)", message, current, total)

        logger.info("[Step 2] Starting extraction with model: %s", selected_chat_model)
        result, from_cache = extract_topics(
            raw_text,
            model=selected_chat_model,
            use_cache=use_cache,
            progress_callback=update_progress,
        )
        progress_bar.empty()
        status_text.empty()

        st.session_state["extracted"] = result
        if from_cache:
            logger.info("[Step 2] Loaded from cache")
            st.info("Loaded from cache.")
        elif result.get("_partial"):
            logger.warning(
                "[Step 2] Partial extraction: %d/%d chunks",
                result.get("_completed_chunks", 0),
                result.get("_total_chunks", 0),
            )
            st.warning(
                f"Rate limited — extracted {result['_completed_chunks']}/{result['_total_chunks']} chunks. "
                "Cached chunks are saved. Click **Run Extraction** again later to continue."
            )
        else:
            topic_count = len(result.get("topics", []))
            logger.info("[Step 2] Extraction complete: %d topics", topic_count)
            st.success(f"Extraction complete! Found {topic_count} topics.")
else:
    st.info("Upload a PDF to extract topics, or load from cache in the sidebar.")

# --- Step 3: Validate & Edit ---
st.header("3. Validate & Edit")
if "extracted" in st.session_state:
    edited = st.text_area(
        "Edit JSON if needed:",
        json.dumps(st.session_state["extracted"], indent=2),
        height=400,
    )
else:
    st.info("No extracted data yet. Upload a PDF or load from cache.")
    edited = "{}"

# --- Step 4: Save to Knowledge Graph ---
st.header("4. Save to Knowledge Graph")
default_doc_name = st.session_state.get("document_name", "Unknown Document")
document_name = st.text_input(
    "Document name (e.g., Biology_Curriculum_2024.pdf)",
    value=default_doc_name,
    help="This name will be used to create a :Document node in Neo4j",
)

if st.button("Save to Neo4j", type="primary"):
    if not document_name or not document_name.strip():
        st.error("Please provide a document name!")
    elif edited == "{}":
        st.error("No data to save. Extract topics first.")
    else:
        data = json.loads(edited)
        if not data.get("topics"):
            st.error("No topics in the data.")
        else:
            with st.spinner("Saving to Neo4j..."):
                topic_count = len(data.get("topics", []))
                subtopic_count = sum(
                    len(t.get("sub_topics", [])) for t in data.get("topics", [])
                )
                logger.info(
                    "[Step 4] Saving to Neo4j: %s (%d topics, %d subtopics)",
                    document_name.strip(),
                    topic_count,
                    subtopic_count,
                )

                driver = get_driver()
                insert_topics(driver, data, document_name=document_name.strip())
                driver.close()

                logger.info("[Step 4] Saved successfully: %s", document_name.strip())
                st.success(
                    f"Saved to Neo4j! Document: **{document_name.strip()}** "
                    f"({topic_count} topics, {subtopic_count} subtopics)"
                )
                st.session_state["neo4j_saved"] = True
                st.session_state["document_name"] = document_name.strip()
                st.rerun()

# --- Step 5: Knowledge Graph Completion (always visible) ---
st.header("5. Knowledge Graph Completion")
st.write("Discover similar topics using semantic embeddings.")

# Get available documents for selector
try:
    driver = get_driver()
    available_docs = get_all_documents(driver)
    driver.close()
    doc_names = [d["name"] for d in available_docs]
except Exception:
    doc_names = []

# Scope selection
st.subheader("Scope")
col_scope1, col_scope2 = st.columns(2)

with col_scope1:
    scope_mode = st.radio(
        "Analysis scope",
        options=["all", "single", "cross"],
        format_func=lambda x: {
            "all": "🌐 All Documents",
            "single": "📄 Single Document",
            "cross": "🔗 Cross-Document (selected + related)",
        }[x],
        help="All: Compare all topics across all documents\n"
        "Single: Compare topics within one document only\n"
        "Cross: Compare topics from selected document with all others",
    )

with col_scope2:
    selected_doc = None
    if scope_mode in ["single", "cross"]:
        if doc_names:
            selected_doc = st.selectbox(
                "Select document",
                options=doc_names,
                help="Choose the document to analyze",
            )
        else:
            st.warning("No documents found in the knowledge graph.")

# Show scope info
if scope_mode == "all":
    st.info(f"Will analyze all topics from {len(doc_names)} document(s)")
elif scope_mode == "single" and selected_doc:
    st.info(f"Will analyze topics within **{selected_doc}** only")
elif scope_mode == "cross" and selected_doc:
    st.info(
        f"Will find similarities between **{selected_doc}** and all other documents"
    )

st.divider()

# Threshold and controls
threshold = st.slider("Similarity threshold", 0.5, 1.0, 0.8, 0.05)

if "found_pairs" not in st.session_state:
    st.session_state["found_pairs"] = None

col_find, col_save = st.columns(2)

with col_find:
    if st.button("Find Similar Topics", type="primary"):
        if scope_mode in ["single", "cross"] and not selected_doc:
            st.error("Please select a document first.")
        else:
            progress_bar = st.progress(0, text="Initializing...")
            status_text = st.empty()

            def update_progress(current: int, total: int, message: str):
                if total > 0:
                    progress_bar.progress(current / total, text=f"{message}")
                status_text.info(message)
                logger.info("[Step 5] %s (%d/%d)", message, current, total)

            try:
                driver = get_driver()
                include_cross = scope_mode == "cross"
                doc_filter = None if scope_mode == "all" else selected_doc

                nodes = get_nodes_with_descriptions(
                    driver,
                    document_name=doc_filter,
                    include_cross_doc=include_cross,
                )
                driver.close()

                if not nodes:
                    progress_bar.empty()
                    status_text.warning("No nodes found in the selected scope.")
                else:
                    logger.info(
                        "[Step 5] Analyzing %d nodes (scope: %s, doc: %s)",
                        len(nodes),
                        scope_mode,
                        doc_filter or "all",
                    )

                    names = [n["name"] for n in nodes]
                    descriptions = [n["description"] for n in nodes]
                    pairs = find_similar_pairs(
                        names,
                        descriptions,
                        threshold=threshold,
                        embedding_model=selected_embedding_model,
                        progress_callback=update_progress,
                    )
                    st.session_state["found_pairs"] = pairs
                    st.session_state["pairs_scope"] = {
                        "mode": scope_mode,
                        "document": selected_doc,
                        "node_count": len(nodes),
                    }

                    progress_bar.empty()
                    status_text.empty()
                    logger.info(
                        "[Step 5] Found %d similar pairs from %d nodes",
                        len(pairs),
                        len(nodes),
                    )
                    st.rerun()

            except Exception as e:
                progress_bar.empty()
                status_text.error(f"Error: {e}")
                logger.error("[Step 5] Error: %s", e)

if st.session_state.get("found_pairs"):
    pairs = st.session_state["found_pairs"]
    scope_info = st.session_state.get("pairs_scope", {})

    if pairs:
        st.success(f"Found {len(pairs)} similar pair(s)!")
        if scope_info:
            st.caption(
                f"Scope: {scope_info.get('mode', 'all')} | "
                f"Nodes: {scope_info.get('node_count', '?')} | "
                f"Document: {scope_info.get('document', 'all')}"
            )

        for p in pairs[:20]:
            st.write(
                f"**{p['source']}** ↔ **{p['target']}** (similarity: {p['similarity']:.3f})"
            )
        if len(pairs) > 20:
            st.info(f"Showing 20 of {len(pairs)} pairs.")

        with col_save:
            if st.button("Save relationships to Neo4j", type="primary"):
                progress_bar = st.progress(0, text="Saving to Neo4j...")
                driver = get_driver()
                saved_count = 0
                with driver.session() as session:
                    for i, p in enumerate(pairs):
                        session.run(
                            "MATCH (a {name: $src}), (b {name: $tgt}) "
                            "MERGE (a)-[:SIMILAR_TO {score: $score}]->(b)",
                            src=p["source"],
                            tgt=p["target"],
                            score=p["similarity"],
                        )
                        saved_count += 1
                        if i % 10 == 0:
                            progress_bar.progress(
                                (i + 1) / len(pairs),
                                text=f"Saving {i + 1}/{len(pairs)}...",
                            )
                driver.close()
                progress_bar.progress(1.0, text="Done!")
                logger.info("[Step 5] Saved %d SIMILAR_TO relationships", saved_count)
                st.success(f"Saved {saved_count} relationships to Neo4j!")
                st.session_state["found_pairs"] = None
                st.rerun()
    else:
        st.info("No similar pairs found above the threshold.")
