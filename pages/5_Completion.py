"""Step 5: Knowledge Graph Completion — discover similar konsep and classify relationships."""

import logging

logging.basicConfig(level=logging.WARNING)
logging.getLogger("neo4j").setLevel(logging.ERROR)

import streamlit as st

from src.graph import (
    get_driver,
    get_graph_stats,
    get_all_documents,
    get_nodes_with_descriptions,
    get_similar_relationships,
    create_typed_relationship,
    create_vector_index,
    drop_vector_index,
    get_index_info,
    count_nodes_with_embeddings,
    get_embedding_dimensions,
    store_node_embeddings,
)
from src.completion import (
    find_similar_pairs_ann,
    classify_similar_pairs,
    get_embeddings,
    build_embed_text,
)
from src.config import (
    MODEL_CHOICES,
    EMBEDDING_CHOICES,
    DEFAULT_CHAT_MODEL,
    DEFAULT_EMBEDDING_MODEL,
)
from src.notify import send_notification
from src.streamlit_log_handler import setup_log_capture, render_log_container

logger = logging.getLogger(__name__)

st.set_page_config(page_title="KG Completion", layout="wide")
st.title("Knowledge Graph Completion")
st.write(
    "Discover similar konsep using semantic embeddings, then classify relationships."
)

# Clear logs from previous render
if "log_handler" in st.session_state:
    st.session_state["log_handler"].clear()

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

# --- Check Neo4j data ---
has_neo4j_data = False
try:
    _driver = get_driver()
    _stats = get_graph_stats(_driver)
    _driver.close()
    has_neo4j_data = _stats.get("konsep", _stats.get("topics", 0)) > 0
except Exception:
    pass

if not has_neo4j_data:
    st.warning(
        "No konsep found in the knowledge graph. "
        "Go to the main pipeline page to upload and extract documents first."
    )
    st.stop()

# --- Get available documents ---
try:
    driver = get_driver()
    available_docs = get_all_documents(driver)
    driver.close()
    doc_names = [d["name"] for d in available_docs]
except Exception:
    doc_names = []

# --- Scope selection ---
st.subheader("Scope")
col_scope1, col_scope2 = st.columns(2)

with col_scope1:
    scope_mode = st.radio(
        "Analysis scope",
        options=["all", "single", "cross"],
        format_func=lambda x: {
            "all": "All Documents",
            "single": "Single Document",
            "cross": "Cross-Document (selected + related)",
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

# --- Threshold and controls ---
col_thresh, col_topk = st.columns(2)
with col_thresh:
    threshold = st.slider("Similarity threshold", 0.5, 1.0, 0.85, 0.05)
with col_topk:
    top_k = st.slider(
        "Neighbors per node (top-k)",
        min_value=1,
        max_value=50,
        value=5,
        step=1,
        help="How many nearest neighbors to consider per node. Larger values "
        "find more pairs at the cost of runtime and noise.",
    )

# Show vector index status
try:
    driver = get_driver()
    index_info = get_index_info(driver)
    embedding_stats = count_nodes_with_embeddings(driver)
    driver.close()

    col_stat1, col_stat2 = st.columns(2)
    with col_stat1:
        if index_info.get("exists"):
            st.success(f"Vector index ready ({index_info.get('state', 'ONLINE')})")
        else:
            st.info("Vector index will be created on first run")
    with col_stat2:
        st.caption(
            f"Nodes with embeddings: {embedding_stats['with_embedding']}/{embedding_stats['total']}"
        )
        if embedding_stats["models"]:
            st.caption(f"Models used: {', '.join(embedding_stats['models'])}")
except Exception as e:
    st.warning(f"Could not check index status: {e}")

if "found_pairs" not in st.session_state:
    st.session_state["found_pairs"] = None

col_find, col_save = st.columns(2)

with col_find:
    if st.button("Find Similar Konsep", type="primary"):
        if scope_mode in ["single", "cross"] and not selected_doc:
            st.error("Please select a document first.")
        else:
            log_handler = setup_log_capture("Step 5: Find Similar")
            progress_bar = st.progress(0, text="Initializing...")

            def update_progress(current: int, total: int, message: str):
                if total > 0:
                    progress_bar.progress(current / total, text=f"{message}")
                logger.info("[Completion] %s (%d/%d)", message, current, total)

            try:
                driver = get_driver()
                include_cross = scope_mode == "cross"
                doc_filter = None if scope_mode == "all" else selected_doc

                nodes = get_nodes_with_descriptions(
                    driver,
                    document_name=doc_filter,
                    include_cross_doc=include_cross,
                )

                if not nodes:
                    progress_bar.empty()
                    st.warning("No nodes found in the selected scope.")
                    driver.close()
                else:
                    logger.info(
                        "[Completion] Analyzing %d nodes (scope: %s, doc: %s, method: ann)",
                        len(nodes),
                        scope_mode,
                        doc_filter or "all",
                    )

                    # Get embeddings first
                    combined_texts = [build_embed_text(n) for n in nodes]

                    update_progress(0, len(nodes), "Computing embeddings...")
                    embeddings = get_embeddings(
                        combined_texts,
                        model=selected_embedding_model,
                        progress_callback=update_progress,
                    )

                    # Single-doc scope: the vector index spans the whole graph,
                    # so restrict matches to the filtered node set explicitly.
                    allowed_names = (
                        {n["name"] for n in nodes} if scope_mode == "single" else None
                    )

                    pairs = find_similar_pairs_ann(
                        driver=driver,
                        nodes=nodes,
                        embeddings=embeddings,
                        model=selected_embedding_model,
                        threshold=threshold,
                        top_k=top_k,
                        allowed_names=allowed_names,
                        progress_callback=update_progress,
                    )
                    driver.close()

                    st.session_state["found_pairs"] = pairs
                    st.session_state["pairs_scope"] = {
                        "mode": scope_mode,
                        "document": selected_doc,
                        "node_count": len(nodes),
                    }

                    progress_bar.empty()
                    logger.info(
                        "[Completion] Found %d similar pairs from %d nodes (ann)",
                        len(pairs),
                        len(nodes),
                    )
                    send_notification(
                        "Similarity Search Done", f"Found {len(pairs)} pairs"
                    )
                    st.rerun()

            except Exception as e:
                progress_bar.empty()
                st.error(f"Error: {e}")
                logger.error("[Completion] Error: %s", e)

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

        # Display all pairs in collapsed view
        with st.expander(f"All {len(pairs)} pairs", expanded=False):
            for p in pairs[:50]:
                st.write(
                    f"**{p['source']}** <-> **{p['target']}** (similarity: {p['similarity']:.3f})"
                )
            if len(pairs) > 50:
                st.info(f"Showing 50 of {len(pairs)} pairs.")

        # Save button
        st.subheader("Save to Knowledge Graph")
        if st.button("Save All Pairs", type="primary"):
            progress_bar = st.progress(0, text="Saving to Neo4j...")
            driver = get_driver()
            saved_count = 0
            with driver.session() as session:
                for i, p in enumerate(pairs):
                    # Restrict matches to Konsep/SubKonsep so names that happen
                    # to collide with Bab/Document nodes cannot be linked.
                    # Pairs are written in a canonical direction (sorted) and
                    # should be read with `-[r:SIMILAR_TO]-` (undirected).
                    src, tgt = sorted([p["source"], p["target"]])
                    session.run(
                        "MATCH (a:Konsep|SubKonsep {name: $src}), "
                        "(b:Konsep|SubKonsep {name: $tgt}) "
                        "MERGE (a)-[r:SIMILAR_TO]->(b) "
                        "SET r.score = $score",
                        src=src,
                        tgt=tgt,
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
            logger.info("[Completion] Saved %d SIMILAR_TO relationships", saved_count)
            st.success(f"Saved {saved_count} relationships to Neo4j!")
            st.session_state["found_pairs"] = None
            st.rerun()
    else:
        st.info("No similar pairs found above the threshold.")

# --- Classify Relationships ---
st.divider()
st.subheader("Classify Relationships")
st.write(
    "Use LLM to classify SIMILAR_TO pairs into typed relationships: "
    "`isPrerequisiteOf`, `supports`, `analogousTo`."
)

try:
    driver = get_driver()
    existing_similar = get_similar_relationships(driver)
    driver.close()
except Exception:
    existing_similar = []

if existing_similar:
    st.info(f"{len(existing_similar)} SIMILAR_TO relationships found in the graph.")

    classify_batch_size = st.slider(
        "Classify batch size (pairs per LLM call)",
        min_value=1,
        max_value=20,
        value=10,
        help=(
            "1 = one LLM call per pair (safer, slower). "
            "10 = ~10x fewer requests, much faster, slightly higher failure blast radius per call. "
            "Failed batches are NOT cached and can be retried by rerunning."
        ),
    )

    col_classify, col_info = st.columns([1, 2])
    with col_classify:
        if st.button("Classify Relationships", type="secondary"):
            log_handler = setup_log_capture("Step 5: Classify")
            progress_bar = st.progress(0, text="Classifying...")

            def update_classify_progress(current: int, total: int, message: str):
                if total > 0:
                    progress_bar.progress(current / total, text=message)

            try:
                driver = get_driver()
                classified = classify_similar_pairs(
                    driver,
                    existing_similar,
                    llm_model=selected_chat_model,
                    progress_callback=update_classify_progress,
                    batch_size=classify_batch_size,
                )
                # Save typed relationships to Neo4j
                saved_typed = 0
                for item in classified:
                    if item["rel_type"] != "none":
                        create_typed_relationship(
                            driver,
                            source=item["source"],
                            target=item["target"],
                            rel_type=item["rel_type"],
                            confidence=item.get("confidence"),
                        )
                        saved_typed += 1
                driver.close()
                progress_bar.empty()
                counts = {}
                for item in classified:
                    counts[item["rel_type"]] = counts.get(item["rel_type"], 0) + 1
                msg = (
                    f"Classified {len(classified)} pairs -> "
                    f"{saved_typed} typed relationships saved. "
                    f"({counts})"
                )
                st.success(msg)
                send_notification("Classification Done", f"{saved_typed} relationships")
                st.rerun()
            except Exception as e:
                progress_bar.empty()
                st.error(f"Classification error: {e}")
                logger.error("[Completion] Classification error: %s", e)

    with col_info:
        st.caption(
            "**isPrerequisiteOf**: A must be learned before B\n\n"
            "**supports**: A helps with / is applied in B\n\n"
            "**analogousTo**: A and B share the same pattern (anti-silo signal)"
        )
else:
    st.info("Run SIMILAR_TO discovery first (above), then classify relationships.")

# --- Vector Index Management ---
st.divider()
st.subheader("Vector Index Management")
st.write("Manage Neo4j vector indexes for ANN similarity search.")

try:
    driver = get_driver()
    index_info = get_index_info(driver)
    embedding_stats = count_nodes_with_embeddings(driver)
    driver.close()

    col_info1, col_info2, col_info3 = st.columns(3)
    with col_info1:
        if index_info.get("exists"):
            st.metric("Index Status", index_info.get("state", "ONLINE"))
        else:
            st.metric("Index Status", "Not Created")

    with col_info2:
        st.metric("Nodes with Embeddings", embedding_stats["with_embedding"])

    with col_info3:
        st.metric("Total Nodes", embedding_stats["total"])

    if embedding_stats["models"]:
        st.caption(f"Embedding models used: {', '.join(embedding_stats['models'])}")

    st.divider()

    col_action1, col_action2, col_action3 = st.columns(3)

    with col_action1:
        dimensions = get_embedding_dimensions(selected_embedding_model)
        if st.button(
            "Create/Refresh Index",
            help=f"Create vector index with {dimensions} dimensions for the selected embedding model",
        ):
            try:
                driver = get_driver()
                success = create_vector_index(driver, dimensions=dimensions)
                driver.close()
                if success:
                    st.success(f"Vector index created with {dimensions} dimensions")
                    st.rerun()
                else:
                    st.error("Failed to create vector index")
            except Exception as e:
                st.error(f"Error: {e}")

    with col_action2:
        if st.button(
            "Drop Index",
            help="Remove vector indexes (useful when changing embedding models)",
        ):
            try:
                driver = get_driver()
                success = drop_vector_index(driver)
                driver.close()
                if success:
                    st.success("Vector indexes dropped")
                    st.rerun()
                else:
                    st.error("Failed to drop vector index")
            except Exception as e:
                st.error(f"Error: {e}")

    with col_action3:
        if st.button(
            "Refresh All Embeddings",
            help="Re-embed all nodes with the selected model and store in Neo4j",
        ):
            try:
                driver = get_driver()
                nodes = get_nodes_with_descriptions(driver)
                if not nodes:
                    st.warning("No nodes found to embed")
                    driver.close()
                else:
                    log_handler = setup_log_capture("Step 5: Embeddings")
                    progress_bar = st.progress(0, text="Embedding nodes...")

                    def update_embed_progress(current: int, total: int, message: str):
                        progress_bar.progress(current / total, text=message)

                    # Get embeddings
                    combined_texts = [build_embed_text(n) for n in nodes]
                    embeddings = get_embeddings(
                        combined_texts,
                        model=selected_embedding_model,
                        progress_callback=update_embed_progress,
                    )

                    # Store in Neo4j
                    updated = store_node_embeddings(
                        driver, nodes, embeddings, selected_embedding_model
                    )
                    driver.close()

                    progress_bar.empty()
                    st.success(f"Stored embeddings for {updated} nodes")
                    st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

except Exception as e:
    st.warning(f"Could not connect to Neo4j: {e}")

# --- Output Log Container ---
st.divider()
render_log_container()
