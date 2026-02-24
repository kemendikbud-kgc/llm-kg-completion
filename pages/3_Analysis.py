"""Single Experiment Analysis - Deep dive into experiment results."""

import streamlit as st

from src.experiments import load_experiments, load_experiment

st.set_page_config(page_title="Experiment Analysis", layout="wide")
st.title("Experiment Analysis")

# Load all experiments for selector
experiments = load_experiments()

if not experiments:
    st.info("No experiments saved yet. Run an extraction first.")
    st.stop()

# Experiment selector
experiment_ids = [exp.id for exp in experiments]
selected_id = st.session_state.get("selected_experiment", experiment_ids[0])

# Find index of selected experiment
try:
    default_index = experiment_ids.index(selected_id)
except ValueError:
    default_index = 0

selected_id = st.selectbox(
    "Select Experiment",
    options=experiment_ids,
    index=default_index,
    format_func=lambda x: (
        f"{x[:25]}... ({experiments[experiment_ids.index(x)].document_name[:20]})"
    ),
)

# Load selected experiment
exp = load_experiment(selected_id)
if not exp:
    st.error(f"Experiment {selected_id} not found.")
    st.stop()

st.divider()

# --- Experiment Overview ---
st.subheader("Overview")

col1, col2 = st.columns(2)

with col1:
    st.write("**Experiment ID:**", exp.id)
    st.write("**Timestamp:**", exp.timestamp)
    st.write("**Document:**", exp.document_name)
    if exp.notes:
        st.write("**Notes:**", exp.notes)

with col2:
    st.write("**Model:**", exp.model)
    st.write("**Prompt:**", exp.prompt_name)
    st.write("**Embedding Model:**", exp.embedding_model)
    st.write("**Similarity Threshold:**", exp.similarity_threshold)

st.divider()

# --- Extraction Metrics ---
st.subheader("Extraction Metrics")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Topics", exp.topic_count)
col2.metric("SubTopics", exp.subtopic_count)
col3.metric("Total Nodes", exp.topic_count + exp.subtopic_count)
col4.metric(
    "Avg SubTopics/Topic",
    f"{exp.subtopic_count / max(exp.topic_count, 1):.1f}",
)

# Filter stats
if exp.filter_enabled:
    st.info(
        f"Content filtering was enabled. "
        f"Reduced input by {exp.filter_reduction_percent:.1f}%"
    )

st.divider()

# --- Graph Quality Metrics ---
st.subheader("Graph Quality Metrics")

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "ADC",
    f"{exp.adc:.4f}",
    help="Average Degree Centrality. Higher = more interconnected graph.",
)
col2.metric(
    "Modularity",
    f"{exp.modularity:.4f}",
    help="Community structure quality. Higher = better-defined topic clusters.",
)
col3.metric(
    "Density",
    f"{exp.density:.4f}",
    help="Graph density. Higher = more edges relative to possible edges.",
)
col4.metric(
    "Similar Pairs",
    exp.similar_pairs_count,
    help="Number of SIMILAR_TO relationships discovered.",
)

st.divider()

# --- Configuration Details ---
st.subheader("Configuration Details")

with st.expander("Full Configuration", expanded=False):
    config_data = {
        "Experiment ID": exp.id,
        "Timestamp": exp.timestamp,
        "Document Name": exp.document_name,
        "Chat Model": exp.model,
        "Prompt Name": exp.prompt_name,
        "Embedding Model": exp.embedding_model,
        "Similarity Threshold": exp.similarity_threshold,
        "Filter Enabled": exp.filter_enabled,
        "Filter Reduction (%)": exp.filter_reduction_percent,
    }
    for key, val in config_data.items():
        st.write(f"**{key}:** `{val}`")

# Additional metadata
if exp.metadata:
    with st.expander("Additional Metadata", expanded=False):
        st.json(exp.metadata)

st.divider()

# --- Export Options ---
st.subheader("Export")

col1, col2 = st.columns(2)

with col1:
    import json
    from dataclasses import asdict

    experiment_json = json.dumps(asdict(exp), indent=2, ensure_ascii=False)
    st.download_button(
        "Download as JSON",
        data=experiment_json,
        file_name=f"{exp.id}.json",
        mime="application/json",
    )

with col2:
    # Create markdown summary
    md_content = f"""# Experiment Report: {exp.id}

## Overview
- **Document:** {exp.document_name}
- **Timestamp:** {exp.timestamp}
- **Model:** {exp.model}
- **Prompt:** {exp.prompt_name}

## Extraction Metrics
- Topics: {exp.topic_count}
- SubTopics: {exp.subtopic_count}
- Total Nodes: {exp.topic_count + exp.subtopic_count}

## Graph Quality
- ADC: {exp.adc:.4f}
- Modularity: {exp.modularity:.4f}
- Density: {exp.density:.4f}
- Similar Pairs: {exp.similar_pairs_count}

## Configuration
- Embedding Model: {exp.embedding_model}
- Similarity Threshold: {exp.similarity_threshold}
- Content Filtering: {"Enabled" if exp.filter_enabled else "Disabled"}

## Notes
{exp.notes or "_No notes_"}
"""
    st.download_button(
        "Download as Markdown",
        data=md_content,
        file_name=f"{exp.id}_report.md",
        mime="text/markdown",
    )
