"""Streamlit app - main entry point."""

import json
import logging

import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config

from src.ingestion import extract_text_from_pdf
from src.extraction import extract_topics, CACHE_DIR, _merge_topics
from src.graph import (
    get_driver,
    insert_topics,
    get_all_documents,
    get_graph_stats,
    get_graph_quality_metrics,
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
from src.schemas import SUBJECT_CHOICES, PHASE_CHOICES
from src.health import check_all

logger = logging.getLogger(__name__)

st.set_page_config(page_title="KG Completion Pipeline", layout="wide")
st.title("LLM-Assisted Knowledge Graph Completion")

# --- Custom CSS for step states ---
st.markdown(
    """
<style>
.step-locked {
    opacity: 0.5;
    pointer-events: none;
}
.step-complete {
    border-left: 4px solid #4CAF50;
    padding-left: 10px;
}
.step-active {
    border-left: 4px solid #2196F3;
    padding-left: 10px;
}
.step-status {
    font-size: 0.85em;
    padding: 2px 8px;
    border-radius: 12px;
    margin-left: 8px;
}
.status-done { background-color: #4CAF50; color: white; }
.status-ready { background-color: #2196F3; color: white; }
.status-locked { background-color: #9E9E9E; color: white; }
</style>
""",
    unsafe_allow_html=True,
)


def step_header(step_num: int, title: str, status: str) -> None:
    """Render a step header with status badge."""
    status_map = {
        "done": ("✓ Done", "status-done"),
        "ready": ("● Ready", "status-ready"),
        "locked": ("○ Locked", "status-locked"),
    }
    label, css_class = status_map.get(status, ("", ""))
    st.markdown(
        f'### {step_num}. {title} <span class="step-status {css_class}">{label}</span>',
        unsafe_allow_html=True,
    )


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
            st.session_state["step1_done"] = True
            st.session_state["step2_done"] = True
            st.success("Loaded from cache file.")
            st.rerun()
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
                st.session_state["step1_done"] = True
                st.session_state["step2_done"] = True
                st.success(f"Merged {len(group)} chunks.")
                st.rerun()
        else:
            st.caption("No cached results found.")

# --- Knowledge Graph Explorer (always visible) ---
with st.expander("🔍 Knowledge Graph Explorer", expanded=True):
    col1, col2, col3, col4 = st.columns(4)

    try:
        driver = get_driver()
        stats = get_graph_stats(driver)
        quality = get_graph_quality_metrics(driver)
        driver.close()

        col1.metric("Subjects", stats.get("subjects", 0))
        col2.metric("Documents", stats["documents"])
        col3.metric("Topics", stats["topics"])
        col4.metric("SubTopics", stats["subtopics"])

        # Second row: relations and quality metrics
        col5, col6, col7, col8 = st.columns(4)
        col5.metric("SIMILAR_TO", stats["similar_rels"])
        col6.metric(
            "ADC",
            quality["adc"],
            help="Average Degree Centrality. Higher = more interconnected graph.",
        )
        col7.metric(
            "Modularity",
            quality["modularity"],
            help="Community structure quality. Higher = better-defined topic clusters.",
        )
        col8.metric(
            "Density",
            quality["density"],
            help="Graph density. Higher = more edges relative to possible edges.",
        )

        if st.button("View Graph Details"):
            st.session_state["show_graph_details"] = True

        if st.session_state.get("show_graph_details"):
            st.subheader("Topics Overview")
            driver = get_driver()
            topics = get_all_topics_with_subtopics(driver)
            documents = get_all_documents(driver)
            similar_rels = get_similar_relationships(driver)
            driver.close()

            tab1, tab2, tab3, tab4 = st.tabs(
                ["Documents", "Topics", "Similar Relationships", "Graph Visualization"]
            )

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

            with tab4:
                if topics:
                    # Build nodes and edges for visualization
                    nodes = []
                    edges = []
                    seen_nodes = set()

                    for t in topics:
                        topic_name = t["name"]
                        if topic_name not in seen_nodes:
                            nodes.append(
                                Node(
                                    id=topic_name,
                                    label=topic_name[:20],
                                    size=25,
                                    color="#4CAF50",  # Green for topics
                                )
                            )
                            seen_nodes.add(topic_name)

                        # Add subtopics
                        for s in t.get("subtopics", []):
                            if not s.get("name"):
                                continue
                            sub_name = s["name"]
                            if sub_name not in seen_nodes:
                                nodes.append(
                                    Node(
                                        id=sub_name,
                                        label=sub_name[:20],
                                        size=15,
                                        color="#2196F3",  # Blue for subtopics
                                    )
                                )
                                seen_nodes.add(sub_name)
                            edges.append(
                                Edge(
                                    source=topic_name,
                                    target=sub_name,
                                    color="#9E9E9E",
                                    width=1,
                                )
                            )

                    # Add SIMILAR_TO edges
                    for rel in similar_rels:
                        if rel["source"] in seen_nodes and rel["target"] in seen_nodes:
                            edges.append(
                                Edge(
                                    source=rel["source"],
                                    target=rel["target"],
                                    color="#FF5722",  # Orange for similarity
                                    width=2,
                                    dashes=True,
                                )
                            )

                    # Graph config
                    config = Config(
                        width=800,
                        height=500,
                        directed=True,
                        physics=True,
                        hierarchical=False,
                        nodeHighlightBehavior=True,
                        highlightColor="#F7A7A6",
                        collapsible=False,
                    )

                    st.caption("🟢 Topics | 🔵 SubTopics | 🟠 SIMILAR_TO (dashed)")
                    agraph(nodes=nodes, edges=edges, config=config)
                else:
                    st.info("No data to visualize. Extract and save topics first.")

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

# --- Determine step states ---
has_raw_text = False
has_extracted = "extracted" in st.session_state
has_neo4j_data = False

# Check Neo4j for existing data
try:
    _driver = get_driver()
    _stats = get_graph_stats(_driver)
    _driver.close()
    has_neo4j_data = _stats.get("topics", 0) > 0
except Exception:
    pass

step1_done = st.session_state.get("step1_done", False)
step2_done = st.session_state.get("step2_done", False) or has_extracted
step3_done = has_extracted  # Step 3 is always "ready" if we have data
step4_done = st.session_state.get("neo4j_saved", False)

# --- Step 1: Upload PDF ---
step1_status = "done" if step1_done else "ready"
step_header(1, "Upload Curriculum Document", step1_status)

if step1_done and not st.session_state.get("show_step1", False):
    if st.button("Re-upload a different document", key="reopen_step1"):
        st.session_state["show_step1"] = True
        st.rerun()
    st.caption("Using cached/loaded data. Click above to upload a new document.")
else:
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
        st.session_state["raw_text"] = raw_text
        st.session_state["step1_done"] = True
        has_raw_text = True
        st.text_area("Extracted Text", raw_text, height=200)

# Get raw_text from session if available
if "raw_text" in st.session_state:
    raw_text = st.session_state["raw_text"]
    has_raw_text = True

st.divider()

# --- Step 2: LLM Extraction ---
step2_ready = has_raw_text or step1_done
step2_status = "done" if step2_done else ("ready" if step2_ready else "locked")
step_header(2, "Extract Topics (LLM)", step2_status)

if step2_status == "locked":
    st.info("⏳ Upload a PDF first, or load from cache in the sidebar.")
elif step2_done and not st.session_state.get("show_step2", False):
    topic_count = len(st.session_state.get("extracted", {}).get("topics", []))
    st.success(f"✓ Extraction complete: {topic_count} topics")
    if st.button("Re-run extraction", key="reopen_step2"):
        st.session_state["show_step2"] = True
        st.rerun()
else:
    if has_raw_text:
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

            logger.info(
                "[Step 2] Starting extraction with model: %s", selected_chat_model
            )
            result, from_cache = extract_topics(
                raw_text,
                model=selected_chat_model,
                use_cache=use_cache,
                progress_callback=update_progress,
            )
            progress_bar.empty()
            status_text.empty()

            st.session_state["extracted"] = result
            st.session_state["step2_done"] = True
            st.session_state["show_step2"] = False
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
            st.rerun()
    else:
        st.info("Upload a PDF in Step 1 to extract topics.")

st.divider()

# --- Step 3: Validate & Edit ---
step3_status = "ready" if has_extracted else "locked"
step_header(3, "Validate & Edit", step3_status)

if step3_status == "locked":
    st.info("⏳ Extract topics first (Step 2) or load from cache.")
    edited = "{}"
else:
    # Card-based validation UI
    topics = st.session_state.get("extracted", {}).get("topics", [])

    # Add topic button
    col_add, col_stats = st.columns([1, 3])
    with col_add:
        if st.button("➕ Add Topic", key="add_topic"):
            topics.append({"name": "New Topic", "description": "", "sub_topics": []})
            st.session_state["extracted"]["topics"] = topics
            st.rerun()
    with col_stats:
        total_subtopics = sum(len(t.get("sub_topics", [])) for t in topics)
        st.caption(f"📊 {len(topics)} topics, {total_subtopics} subtopics")

    # Track topics to delete (can't modify list while iterating)
    topics_to_delete = []

    # Render each topic as an expandable card
    for i, topic in enumerate(topics):
        with st.container(border=True):
            col_topic, col_del = st.columns([5, 1])

            with col_topic:
                new_name = st.text_input(
                    f"Topic {i + 1}",
                    value=topic.get("name", ""),
                    key=f"topic_name_{i}",
                    label_visibility="collapsed",
                    placeholder="Topic name",
                )
                if new_name != topic.get("name", ""):
                    topic["name"] = new_name

            with col_del:
                if st.button("🗑️", key=f"del_topic_{i}", help="Delete this topic"):
                    topics_to_delete.append(i)

            new_desc = st.text_area(
                "Description",
                value=topic.get("description", ""),
                key=f"topic_desc_{i}",
                height=80,
                label_visibility="collapsed",
                placeholder="Topic description",
            )
            if new_desc != topic.get("description", ""):
                topic["description"] = new_desc

            # SubTopics section
            subtopics = topic.get("sub_topics", [])
            subtopics_to_delete = []

            with st.expander(f"📑 SubTopics ({len(subtopics)})", expanded=False):
                if st.button(
                    "➕ Add SubTopic", key=f"add_sub_{i}", use_container_width=True
                ):
                    subtopics.append({"name": "New SubTopic", "description": ""})
                    topic["sub_topics"] = subtopics
                    st.rerun()

                for j, sub in enumerate(subtopics):
                    cols = st.columns([3, 4, 1])
                    with cols[0]:
                        new_sub_name = st.text_input(
                            "Name",
                            value=sub.get("name", ""),
                            key=f"sub_name_{i}_{j}",
                            label_visibility="collapsed",
                            placeholder="SubTopic name",
                        )
                        if new_sub_name != sub.get("name", ""):
                            sub["name"] = new_sub_name
                    with cols[1]:
                        new_sub_desc = st.text_input(
                            "Description",
                            value=sub.get("description", ""),
                            key=f"sub_desc_{i}_{j}",
                            label_visibility="collapsed",
                            placeholder="SubTopic description",
                        )
                        if new_sub_desc != sub.get("description", ""):
                            sub["description"] = new_sub_desc
                    with cols[2]:
                        if st.button("🗑️", key=f"del_sub_{i}_{j}"):
                            subtopics_to_delete.append(j)

                # Delete marked subtopics (reverse order to preserve indices)
                for j in reversed(subtopics_to_delete):
                    subtopics.pop(j)
                    st.rerun()

    # Delete marked topics (reverse order to preserve indices)
    if topics_to_delete:
        for i in reversed(topics_to_delete):
            topics.pop(i)
        st.session_state["extracted"]["topics"] = topics
        st.rerun()

    # Update session state with edited data
    st.session_state["extracted"]["topics"] = topics

    # Generate edited JSON for Step 4 compatibility
    edited = json.dumps(st.session_state["extracted"], indent=2, ensure_ascii=False)

    # Show raw JSON in collapsible section for debugging
    with st.expander("📝 View/Edit Raw JSON", expanded=False):
        raw_edited = st.text_area(
            "Raw JSON (edit with caution):",
            edited,
            height=300,
            key="raw_json_editor",
        )
        if raw_edited != edited:
            try:
                parsed = json.loads(raw_edited)
                st.session_state["extracted"] = parsed
                edited = raw_edited
                st.success("JSON updated!")
            except json.JSONDecodeError as e:
                st.error(f"Invalid JSON: {e}")

st.divider()

# --- Step 4: Save to Knowledge Graph ---
step4_status = "done" if step4_done else ("ready" if has_extracted else "locked")
step_header(4, "Save to Knowledge Graph", step4_status)

if step4_status == "locked":
    st.info("⏳ Extract and validate topics first (Steps 2-3).")
elif step4_done and not st.session_state.get("show_step4", False):
    st.success(f"✓ Saved to Neo4j: {st.session_state.get('document_name', 'Document')}")
    if st.button("Save again (update)", key="reopen_step4"):
        st.session_state["show_step4"] = True
        st.rerun()
else:
    default_doc_name = st.session_state.get("document_name", "Unknown Document")
    document_name = st.text_input(
        "Document name (e.g., Biology_Curriculum_2024.pdf)",
        value=default_doc_name,
        help="This name will be used to create a :Document node in Neo4j",
    )

    # Subject metadata (Kurikulum Merdeka alignment)
    st.subheader("📚 Subject Metadata (optional)")
    col_subj, col_phase = st.columns(2)

    with col_subj:
        subject_name = st.selectbox(
            "Mata Pelajaran (Subject)",
            options=["(None)"] + SUBJECT_CHOICES,
            index=0,
            help="Select the curriculum subject this document belongs to",
        )
        if subject_name == "(None)":
            subject_name = None

    with col_phase:
        phase_key = st.selectbox(
            "Fase (Phase)",
            options=["(None)"] + list(PHASE_CHOICES.keys()),
            format_func=lambda x: PHASE_CHOICES.get(x, "(None)"),
            index=0,
            help="Kurikulum Merdeka phase: E (Kelas X) or F (Kelas XI-XII)",
        )
        if phase_key == "(None)":
            phase_key = None

    if subject_name:
        st.caption(
            f"Will create: `(:Subject {{name: '{subject_name}', phase: '{phase_key or ''}'}})-[:CONTAINS]->(:Document)`"
        )

    st.divider()

    if st.button("Save to Neo4j", type="primary", disabled=(edited == "{}")):
        if not document_name or not document_name.strip():
            st.error("Please provide a document name!")
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
                        "[Step 4] Saving to Neo4j: %s (%d topics, %d subtopics, subject: %s)",
                        document_name.strip(),
                        topic_count,
                        subtopic_count,
                        subject_name or "none",
                    )

                    driver = get_driver()
                    insert_topics(
                        driver,
                        data,
                        document_name=document_name.strip(),
                        subject_name=subject_name,
                        subject_phase=phase_key,
                    )
                    driver.close()

                    logger.info(
                        "[Step 4] Saved successfully: %s", document_name.strip()
                    )
                    subject_info = f", Subject: {subject_name}" if subject_name else ""
                    st.success(
                        f"Saved to Neo4j! Document: **{document_name.strip()}** "
                        f"({topic_count} topics, {subtopic_count} subtopics{subject_info})"
                    )
                    st.session_state["neo4j_saved"] = True
                    st.session_state["show_step4"] = False
                    st.session_state["document_name"] = document_name.strip()
                    st.rerun()

st.divider()

# --- Step 5: Knowledge Graph Completion ---
step5_status = "ready" if has_neo4j_data else "locked"
step_header(5, "Knowledge Graph Completion", step5_status)

if step5_status == "locked":
    st.info("⏳ Save topics to Neo4j first (Step 4).")
else:
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

            # Semi-supervised validation mode for large result sets
            SAMPLE_SIZE = 10
            if len(pairs) > SAMPLE_SIZE:
                st.subheader("🔍 Semi-Supervised Validation")
                st.write(
                    f"Review a sample of {SAMPLE_SIZE} pairs to estimate precision. "
                    "Mark each pair as valid or invalid."
                )

                # Initialize validation state if not present
                if "validation_sample" not in st.session_state:
                    import random

                    sample_indices = random.sample(range(len(pairs)), SAMPLE_SIZE)
                    st.session_state["validation_sample"] = sample_indices
                    st.session_state["validation_results"] = {}

                sample_indices = st.session_state["validation_sample"]
                validation_results = st.session_state["validation_results"]

                # Display sample pairs for validation
                for idx in sample_indices:
                    p = pairs[idx]
                    pair_key = f"{p['source']}|{p['target']}"

                    with st.container(border=True):
                        cols = st.columns([4, 1, 1])
                        with cols[0]:
                            st.write(
                                f"**{p['source']}** ↔ **{p['target']}** "
                                f"(score: {p['similarity']:.3f})"
                            )
                        with cols[1]:
                            if st.button("✅ Valid", key=f"valid_{idx}"):
                                validation_results[pair_key] = True
                                st.rerun()
                        with cols[2]:
                            if st.button("❌ Invalid", key=f"invalid_{idx}"):
                                validation_results[pair_key] = False
                                st.rerun()

                        # Show current status
                        if pair_key in validation_results:
                            status = (
                                "✅ Valid"
                                if validation_results[pair_key]
                                else "❌ Invalid"
                            )
                            st.caption(f"Status: {status}")

                # Calculate precision
                validated_count = len(validation_results)
                valid_count = sum(1 for v in validation_results.values() if v)

                st.divider()
                col_prec, col_resample = st.columns(2)

                with col_prec:
                    if validated_count > 0:
                        precision = valid_count / validated_count
                        st.metric(
                            "Estimated Precision",
                            f"{precision:.0%}",
                            help=f"Based on {validated_count}/{SAMPLE_SIZE} validated samples",
                        )
                        st.caption(f"Validated: {validated_count}/{SAMPLE_SIZE} pairs")
                    else:
                        st.info("Validate some pairs to see precision estimate.")

                with col_resample:
                    if st.button("🔄 New Sample", help="Get a new random sample"):
                        import random

                        st.session_state["validation_sample"] = random.sample(
                            range(len(pairs)), SAMPLE_SIZE
                        )
                        st.session_state["validation_results"] = {}
                        st.rerun()

                st.divider()

            # Display all pairs (or remaining pairs in collapsed view)
            with st.expander(
                f"📋 All {len(pairs)} pairs"
                if len(pairs) > SAMPLE_SIZE
                else "📋 Similar pairs",
                expanded=len(pairs) <= SAMPLE_SIZE,
            ):
                for p in pairs[:50]:
                    st.write(
                        f"**{p['source']}** ↔ **{p['target']}** (similarity: {p['similarity']:.3f})"
                    )
                if len(pairs) > 50:
                    st.info(f"Showing 50 of {len(pairs)} pairs.")

            # Save options
            st.subheader("💾 Save to Knowledge Graph")
            save_col1, save_col2 = st.columns(2)

            with save_col1:
                if st.button("Save All Pairs", type="primary"):
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
                    logger.info(
                        "[Step 5] Saved %d SIMILAR_TO relationships", saved_count
                    )
                    st.success(f"Saved {saved_count} relationships to Neo4j!")
                    # Clear validation state
                    st.session_state.pop("validation_sample", None)
                    st.session_state.pop("validation_results", None)
                    st.session_state["found_pairs"] = None
                    st.rerun()

            with save_col2:
                if len(pairs) > SAMPLE_SIZE:
                    validation_results = st.session_state.get("validation_results", {})
                    if validation_results:
                        # Get validated pairs that were marked as valid
                        validated_pairs = [
                            p
                            for p in pairs
                            if validation_results.get(
                                f"{p['source']}|{p['target']}", True
                            )
                        ]
                        invalid_count = sum(
                            1 for v in validation_results.values() if not v
                        )

                        if st.button(
                            f"Save Excluding Invalid ({len(pairs) - invalid_count} pairs)",
                            help="Save all pairs except those marked as invalid in validation",
                        ):
                            progress_bar = st.progress(0, text="Saving to Neo4j...")
                            driver = get_driver()
                            saved_count = 0
                            pairs_to_save = [
                                p
                                for p in pairs
                                if validation_results.get(
                                    f"{p['source']}|{p['target']}", True
                                )
                            ]
                            with driver.session() as session:
                                for i, p in enumerate(pairs_to_save):
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
                                            (i + 1) / len(pairs_to_save),
                                            text=f"Saving {i + 1}/{len(pairs_to_save)}...",
                                        )
                            driver.close()
                            progress_bar.progress(1.0, text="Done!")
                            logger.info(
                                "[Step 5] Saved %d SIMILAR_TO relationships (excluded %d invalid)",
                                saved_count,
                                invalid_count,
                            )
                            st.success(
                                f"Saved {saved_count} relationships (excluded {invalid_count} invalid)!"
                            )
                            st.session_state.pop("validation_sample", None)
                            st.session_state.pop("validation_results", None)
                            st.session_state["found_pairs"] = None
                            st.rerun()
        else:
            st.info("No similar pairs found above the threshold.")
