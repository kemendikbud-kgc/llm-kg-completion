"""Step 5: Knowledge Graph Completion — discover similar konsep and classify relationships."""

import logging

logging.basicConfig(level=logging.WARNING)
logging.getLogger("neo4j").setLevel(logging.ERROR)

import streamlit as st

from src.completion import (
    find_similar_pairs_ann,
    classify_similar_pairs,
    get_embeddings,
    build_embed_text,
    dump_lintas_buku_results,
)
from src.config import (
    MODEL_CHOICES,
    EMBEDDING_CHOICES,
    DEFAULT_CHAT_MODEL,
    DEFAULT_EMBEDDING_MODEL,
)
from src.connection import CONNECTION_TARGETS, Neo4jConnection
from src.graph import get_embedding_dimensions
from src.notify import send_notification
from src.schema_adapter import get_adapter
from src.streamlit_log_handler import setup_log_capture, render_log_container

logger = logging.getLogger(__name__)

st.set_page_config(page_title="KG Completion", layout="wide")
st.title("Knowledge Graph Completion")
st.write(
    "Discover similar concepts using semantic embeddings, then classify relationships."
)

# Clear logs from previous render
if "log_handler" in st.session_state:
    st.session_state["log_handler"].clear()

# --- Sidebar: Schema + Connection + Model Selection ---
with st.sidebar:
    st.header("Database Schema")
    schema_name = st.selectbox(
        "Schema (ontology)",
        options=["soros", "yhoga"],
        index=0,
        help=(
            "soros: Konsep/SubKonsep ontology.\n"
            "yhoga: Concept/Subtopic/Chapter/Grade ontology.\n\n"
            "Schema is independent of which Neo4j DB you target — pick the connection below."
        ),
    )

    # Connection target — independent of schema. "auto" preserves legacy
    # behavior (soros→default DB, yhoga→yhoga DB). Override to run e.g. the
    # yhoga ontology against the project's own upstream.
    target_options = ["auto"] + list(CONNECTION_TARGETS.keys())
    connection_target = st.selectbox(
        "Neo4j target",
        options=target_options,
        index=0,
        help=(
            "auto: use the schema's default DB (legacy soros→NEO4J_URI, yhoga→NEO4J_URI_YHOGA).\n"
            "default: force NEO4J_URI (your own Neo4j upstream).\n"
            "yhoga: force NEO4J_URI_YHOGA (peer-owned Yhoga Aura)."
        ),
    )

    explicit_conn: Neo4jConnection | None = None
    if connection_target != "auto":
        try:
            explicit_conn = Neo4jConnection.by_name(connection_target)
        except ValueError as e:
            st.error(str(e))
            st.stop()

    adapter = get_adapter(schema_name, connection=explicit_conn)
    spec = adapter.spec
    active_label = adapter.connection_label()
    st.caption(
        f"Labels: `{', '.join(spec.node_labels)}` · "
        f"Index: `{', '.join(spec.index_names.values())}` · "
        f"DB: `{active_label}`"
    )

    # If the user switches schema OR connection we want to drop stale state
    # (similar pairs found on the previous DB are not valid on the new one).
    session_key = (schema_name, active_label)
    if st.session_state.get("active_schema_db") != session_key:
        st.session_state["active_schema_db"] = session_key
        st.session_state["active_schema"] = schema_name
        st.session_state["found_pairs"] = None
        st.session_state.pop("pairs_scope", None)

    st.divider()
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

# --- Check Neo4j data on the selected schema ---
has_neo4j_data = False
connection_error: str | None = None
try:
    _driver = adapter.get_driver()
    has_neo4j_data = adapter.get_total_concept_count(_driver) > 0
    _driver.close()
except Exception as e:
    connection_error = str(e)

if connection_error:
    db_hint = (
        f"connection target `{adapter.connection.label}` "
        f"(uri `{adapter.connection.uri[:30]}…`)"
        if adapter.connection is not None
        else f"env vars `{spec.neo4j_uri_env}` / `{spec.neo4j_password_env}`"
    )
    st.error(
        f"Could not connect with **{schema_name}** schema on {db_hint}:\n\n{connection_error}"
    )
    st.stop()

if not has_neo4j_data:
    st.warning(
        f"No concepts found in the **{schema_name}** knowledge graph. "
        + (
            "Go to the main pipeline page to upload and extract documents first."
            if schema_name == "soros"
            else "The yhoga DB is read-only here — verify the connection points to the right Aura instance."
        )
    )
    st.stop()

# --- Get available documents for the selected schema ---
try:
    driver = adapter.get_driver()
    available_docs = adapter.get_documents(driver)
    driver.close()
    doc_names = [d["name"] for d in available_docs]
except Exception:
    doc_names = []

# --- Index Setup (collapsible, prerequisite for similarity search) ---
with st.expander("⚙️ Index Setup", expanded=False):
    st.caption(
        "Vector index and node embeddings. Expand only when changing embedding "
        "models or rebuilding the index."
    )
    try:
        driver = adapter.get_driver()
        index_info = adapter.get_index_info(driver)
        embedding_stats = adapter.count_nodes_with_embeddings(driver)
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
            st.caption(
                f"Embedding models used: {', '.join(embedding_stats['models'])}"
            )

        st.divider()

        col_action1, col_action2, col_action3 = st.columns(3)

        with col_action1:
            dimensions = get_embedding_dimensions(selected_embedding_model)
            if st.button(
                "Create/Refresh Index",
                help=f"Create vector index with {dimensions} dimensions for the selected embedding model",
            ):
                try:
                    driver = adapter.get_driver()
                    success = adapter.create_vector_indexes(driver, dimensions=dimensions)
                    driver.close()
                    if success:
                        st.success(
                            f"Vector index created with {dimensions} dimensions"
                        )
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
                    driver = adapter.get_driver()
                    success = adapter.drop_vector_indexes(driver)
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
                    driver = adapter.get_driver()
                    nodes = adapter.get_nodes_for_completion(driver)
                    if not nodes:
                        st.warning("No nodes found to embed")
                        driver.close()
                    else:
                        log_handler = setup_log_capture("Step 5: Embeddings")
                        progress_bar = st.progress(0, text="Embedding nodes...")

                        def update_embed_progress(
                            current: int, total: int, message: str
                        ):
                            progress_bar.progress(current / total, text=message)

                        combined_texts = [build_embed_text(n, adapter=adapter) for n in nodes]
                        embeddings = get_embeddings(
                            combined_texts,
                            model=selected_embedding_model,
                            progress_callback=update_embed_progress,
                        )

                        updated = adapter.store_node_embeddings(
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

# --- Scope selection ---
st.subheader("Scope")
col_scope1, col_scope2 = st.columns(2)

doc_term = "Grade" if schema_name == "yhoga" else "Document"

with col_scope1:
    scope_mode = st.radio(
        "Analysis scope",
        options=["all", "single", "cross", "cross_all"],
        format_func=lambda x: {
            "all": f"All {doc_term}s",
            "single": f"Single {doc_term}",
            "cross": f"Cross-{doc_term} (selected + related)",
            "cross_all": f"All Cross-{doc_term} (full sweep, no selection)",
        }[x],
        help=(
            f"All: Compare all concepts across all {doc_term.lower()}s (intra + cross).\n"
            f"Single: Compare concepts within one {doc_term.lower()} only.\n"
            f"Cross: One {doc_term.lower()} queries; partners can come from any other (1 anchor).\n"
            f"All Cross: every {doc_term.lower()} queries; only cross-{doc_term.lower()} pairs kept "
            f"(matches ann-v1 Iter 2 canonical run)."
        ),
    )

with col_scope2:
    selected_doc = None
    if scope_mode in ["single", "cross"]:
        if doc_names:
            selected_doc = st.selectbox(
                f"Select {doc_term.lower()}",
                options=doc_names,
                help=f"Choose the {doc_term.lower()} to analyze",
            )
        else:
            st.warning(f"No {doc_term.lower()}s found in the knowledge graph.")
    elif scope_mode == "cross_all":
        st.caption(f"No {doc_term.lower()} selection — every concept is a query.")

# Show scope info
if scope_mode == "all":
    st.info(f"Will analyze all concepts from {len(doc_names)} {doc_term.lower()}(s)")
elif scope_mode == "single" and selected_doc:
    st.info(f"Will analyze concepts within **{selected_doc}** only")
elif scope_mode == "cross" and selected_doc:
    st.info(
        f"Will find similarities between **{selected_doc}** and all other {doc_term.lower()}s"
    )
elif scope_mode == "cross_all":
    st.info(
        f"Will find all cross-{doc_term.lower()} similarities across "
        f"{len(doc_names)} {doc_term.lower()}(s) (every concept queries the index, "
        f"only cross-{doc_term.lower()} pairs kept)."
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

if "found_pairs" not in st.session_state:
    st.session_state["found_pairs"] = None

col_find, col_save = st.columns(2)

with col_find:
    if st.button("Find Similar Concepts", type="primary"):
        if scope_mode in ["single", "cross"] and not selected_doc:
            st.error(f"Please select a {doc_term.lower()} first.")
        else:
            log_handler = setup_log_capture("Step 5: Find Similar")
            progress_bar = st.progress(0, text="Initializing...")

            def update_progress(current: int, total: int, message: str):
                if total > 0:
                    progress_bar.progress(current / total, text=f"{message}")
                logger.info("[Completion] %s (%d/%d)", message, current, total)

            try:
                driver = adapter.get_driver()
                # `include_cross` controls whether nodes from OTHER docs are
                # fetched as eligible partners. True for cross (single-anchor)
                # and cross_all (every concept queries) — both want full graph.
                include_cross = scope_mode in ("cross", "cross_all")
                # `doc_filter` restricts the QUERY set. None means "every node
                # in the graph queries the index".
                doc_filter = None if scope_mode in ("all", "cross_all") else selected_doc

                nodes = adapter.get_nodes_for_completion(
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
                        "[Completion] Analyzing %d nodes (schema: %s, scope: %s, doc: %s, method: ann)",
                        len(nodes),
                        schema_name,
                        scope_mode,
                        doc_filter or "all",
                    )

                    # Get embeddings first
                    combined_texts = [build_embed_text(n, adapter=adapter) for n in nodes]

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

                    # Yhoga + (cross | cross_all) scope = LINTAS_BUKU completion.
                    # The TTL ontology defines LINTAS_BUKU_* strictly across different
                    # grades, so enforce that as a hard filter at pair generation.
                    cross_grade_only = (
                        schema_name == "yhoga"
                        and scope_mode in ("cross", "cross_all")
                    )
                    # Skip pairs already typed-connected (rule iii): if A and B
                    # already share a non-SIMILAR_TO edge, don't rediscover them.
                    # Applies always for Yhoga — within-grade redundancy from
                    # extraction and cross-grade LINTAS_BUKU edges from prior
                    # completion runs are both filtered out.
                    skip_existing_typed_edges = schema_name == "yhoga"

                    pairs = find_similar_pairs_ann(
                        driver=driver,
                        nodes=nodes,
                        embeddings=embeddings,
                        model=selected_embedding_model,
                        threshold=threshold,
                        top_k=top_k,
                        allowed_names=allowed_names,
                        progress_callback=update_progress,
                        adapter=adapter,
                        cross_grade_only=cross_grade_only,
                        skip_existing_typed_edges=skip_existing_typed_edges,
                    )
                    driver.close()

                    st.session_state["found_pairs"] = pairs
                    st.session_state["pairs_scope"] = {
                        "schema": schema_name,
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
                f"Schema: {scope_info.get('schema', '?')} | "
                f"Scope: {scope_info.get('mode', 'all')} | "
                f"Nodes: {scope_info.get('node_count', '?')} | "
                f"{doc_term}: {scope_info.get('document', 'all')}"
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
            driver = adapter.get_driver()
            saved_count = 0
            for i, p in enumerate(pairs):
                adapter.save_similar_pair(
                    driver,
                    source=p["source"],
                    target=p["target"],
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
if schema_name == "yhoga":
    st.write(
        "Use LLM to classify SIMILAR_TO pairs into Yhoga's 5-type closed "
        "**LINTAS_BUKU_\\*** vocabulary (per `docs/yhoga-ontology.ttl`): "
        "`SAMA_DENGAN`, `APLIKASI_DARI`, `PRASYARAT_UNTUK`, `MEMPERDALAM`, "
        "`BERKAITAN_DENGAN`. Output is staged to JSON, not written directly "
        "to Neo4j — review then replay via `experiments/scripts/replay_completion.py`."
    )
else:
    st.write(
        "Use LLM to classify SIMILAR_TO pairs into typed relationships: "
        "`isPrerequisiteOf`, `supports`, `analogousTo`."
    )

try:
    driver = adapter.get_driver()
    existing_similar = adapter.get_similar_pairs(driver)
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

    # Yhoga staging output path (canonical experiment folder).
    default_yhoga_output = (
        "experiments/knowledge_graph_states/completion-experiments/"
        "ann-classifier-v1/lintas_buku_edges.json"
    )
    yhoga_output_path = (
        st.text_input(
            "JSON staging path",
            value=default_yhoga_output,
            help=(
                "LINTAS_BUKU_* edges are written here for audit. Replay into "
                "Neo4j via `python experiments/scripts/replay_completion.py <path>`."
            ),
        )
        if schema_name == "yhoga"
        else None
    )

    col_classify, col_info = st.columns([1, 2])
    with col_classify:
        button_label = (
            "Classify & Stage to JSON"
            if schema_name == "yhoga"
            else "Classify Relationships"
        )
        if st.button(button_label, type="secondary"):
            log_handler = setup_log_capture("Step 5: Classify")
            progress_bar = st.progress(0, text="Classifying...")

            def update_classify_progress(current: int, total: int, message: str):
                if total > 0:
                    progress_bar.progress(current / total, text=message)

            try:
                driver = adapter.get_driver()
                classified = classify_similar_pairs(
                    driver,
                    existing_similar,
                    llm_model=selected_chat_model,
                    progress_callback=update_classify_progress,
                    batch_size=classify_batch_size,
                    adapter=adapter,
                )

                counts: dict[str, int] = {}
                for item in classified:
                    counts[item["rel_type"]] = counts.get(item["rel_type"], 0) + 1

                if schema_name == "yhoga":
                    # Stage to JSON — do not touch Yhoga Neo4j here. Replay
                    # script handles the MERGE-into-Neo4j step separately.
                    written = dump_lintas_buku_results(
                        classified,
                        output_path=yhoga_output_path,
                        driver=driver,
                        version="ann-classifier-v1",
                        source_state="extraction-v2-reviewed",
                        method="ann + classifier",
                        params={
                            "embed_model": selected_embedding_model,
                            "chat_model": selected_chat_model,
                            "threshold": float(threshold),
                            "top_k": int(top_k),
                            "scope": scope_mode,
                            "selected_doc": selected_doc,
                            "batch_size": int(classify_batch_size),
                        },
                    )
                    driver.close()
                    progress_bar.empty()
                    st.success(
                        f"Classified {len(classified)} pairs → staged {written} "
                        f"LINTAS_BUKU_* edges to `{yhoga_output_path}`. ({counts})"
                    )
                    st.caption(
                        "Next: review the JSON, then run "
                        "`python experiments/scripts/replay_completion.py "
                        f"{yhoga_output_path}` to MERGE into Yhoga Neo4j."
                    )
                    send_notification(
                        "Classification Staged", f"{written} edges to JSON"
                    )
                else:
                    # Soros: direct write to Neo4j (legacy behavior).
                    saved_typed = 0
                    for item in classified:
                        if item["rel_type"] != "none":
                            adapter.save_typed_relationship(
                                driver,
                                source=item["source"],
                                target=item["target"],
                                rel_type=item["rel_type"],
                                confidence=item.get("confidence"),
                            )
                            saved_typed += 1
                    driver.close()
                    progress_bar.empty()
                    st.success(
                        f"Classified {len(classified)} pairs -> "
                        f"{saved_typed} typed relationships saved. ({counts})"
                    )
                    send_notification(
                        "Classification Done", f"{saved_typed} relationships"
                    )
                st.rerun()
            except Exception as e:
                progress_bar.empty()
                st.error(f"Classification error: {e}")
                logger.error("[Completion] Classification error: %s", e)

    with col_info:
        if schema_name == "yhoga":
            st.caption(
                "**LINTAS_BUKU_SAMA_DENGAN**: konsep yang sama di buku berbeda (simetris).\n\n"
                "**LINTAS_BUKU_APLIKASI_DARI**: A adalah penerapan konsep B di disiplin lain.\n\n"
                "**LINTAS_BUKU_PRASYARAT_UNTUK**: A prasyarat memahami B di mata pelajaran lain.\n\n"
                "**LINTAS_BUKU_MEMPERDALAM**: A memperdalam pemahaman B di buku lain.\n\n"
                "**LINTAS_BUKU_BERKAITAN_DENGAN**: berkaitan umum (fallback, simetris)."
            )
        else:
            st.caption(
                "**isPrerequisiteOf**: A must be learned before B\n\n"
                "**supports**: A helps with / is applied in B\n\n"
                "**analogousTo**: A and B share the same pattern (anti-silo signal)"
            )
else:
    st.info(
        "No SIMILAR_TO relationships yet. Run **Find Similar Concepts** above first, "
        "then return here to classify them."
    )

# --- Output Log Container ---
st.divider()
render_log_container()
