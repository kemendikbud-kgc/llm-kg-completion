"""Experiments Dashboard - Compare extraction configurations."""

import streamlit as st

from src.experiments import (
    load_experiments,
    compare_experiments,
    delete_experiment,
    get_experiment_summary,
)

st.set_page_config(page_title="Experiments Dashboard", layout="wide")
st.title("Experiments Dashboard")
st.write("Compare different extraction configurations and their results.")

# Load all experiments
experiments = load_experiments()

if not experiments:
    st.info(
        "No experiments saved yet. Run an extraction in the Pipeline page "
        "and click 'Save as Experiment' to start tracking."
    )
    st.stop()

# --- Experiment List ---
st.subheader(f"Saved Experiments ({len(experiments)})")

# Create columns for experiment cards
cols_per_row = 3
selected_for_comparison = []

for i in range(0, len(experiments), cols_per_row):
    cols = st.columns(cols_per_row)
    for j, col in enumerate(cols):
        idx = i + j
        if idx >= len(experiments):
            break

        exp = experiments[idx]
        summary = get_experiment_summary(exp)

        with col:
            with st.container(border=True):
                # Header with checkbox
                col_check, col_title = st.columns([1, 4])
                with col_check:
                    is_selected = st.checkbox(
                        "Select",
                        key=f"select_{exp.id}",
                        label_visibility="collapsed",
                    )
                    if is_selected:
                        selected_for_comparison.append(exp)
                with col_title:
                    st.markdown(f"**{exp.id[:20]}...**")

                # Metadata
                st.caption(f"{exp.timestamp[:10]}")
                st.write(f"**Doc:** {exp.document_name[:30]}")
                st.write(f"**Model:** {summary['model']}")
                st.write(f"**Prompt:** {exp.prompt_name}")

                # Metrics
                col_t, col_s = st.columns(2)
                col_t.metric("Topics", exp.topic_count)
                col_s.metric("SubTopics", exp.subtopic_count)

                col_adc, col_pairs = st.columns(2)
                col_adc.metric("ADC", summary["adc"])
                col_pairs.metric("Similar Pairs", exp.similar_pairs_count)

                # Actions
                col_view, col_del = st.columns(2)
                with col_view:
                    if st.button("View Details", key=f"view_{exp.id}"):
                        st.session_state["selected_experiment"] = exp.id
                        st.switch_page("pages/3_Analysis.py")
                with col_del:
                    if st.button("Delete", key=f"del_{exp.id}"):
                        if delete_experiment(exp.id):
                            st.success(f"Deleted {exp.id}")
                            st.rerun()

st.divider()

# --- Comparison Section ---
st.subheader("Compare Experiments")

if len(selected_for_comparison) < 2:
    st.info("Select 2 experiments above to compare them.")
elif len(selected_for_comparison) > 2:
    st.warning("Please select exactly 2 experiments to compare.")
else:
    exp1, exp2 = selected_for_comparison[0], selected_for_comparison[1]
    comparison = compare_experiments(exp1, exp2)

    st.write(f"Comparing **{exp1.id[:15]}...** vs **{exp2.id[:15]}...**")

    # Configuration differences
    config_changes = comparison["config_changes"]
    has_config_changes = any(v for v in config_changes.values() if v)

    if has_config_changes:
        st.subheader("Configuration Differences")
        for key, val in config_changes.items():
            if val:
                st.write(f"- **{key}:** `{val[0]}` -> `{val[1]}`")
    else:
        st.info("Same configuration used for both experiments.")

    # Metric comparison
    st.subheader("Metric Comparison")

    col1, col2, col3 = st.columns(3)

    with col1:
        delta = comparison["topic_diff"]
        st.metric(
            "Topic Count",
            f"{exp1.topic_count} vs {exp2.topic_count}",
            delta=delta if delta != 0 else None,
            delta_color="normal",
        )

    with col2:
        delta = comparison["subtopic_diff"]
        st.metric(
            "SubTopic Count",
            f"{exp1.subtopic_count} vs {exp2.subtopic_count}",
            delta=delta if delta != 0 else None,
            delta_color="normal",
        )

    with col3:
        delta = comparison["pairs_diff"]
        st.metric(
            "Similar Pairs",
            f"{exp1.similar_pairs_count} vs {exp2.similar_pairs_count}",
            delta=delta if delta != 0 else None,
            delta_color="normal",
        )

    col4, col5, col6 = st.columns(3)

    with col4:
        delta = comparison["adc_diff"]
        st.metric(
            "ADC",
            f"{exp1.adc:.3f} vs {exp2.adc:.3f}",
            delta=f"{delta:.3f}" if abs(delta) > 0.001 else None,
            delta_color="normal",
        )

    with col5:
        delta = comparison["modularity_diff"]
        st.metric(
            "Modularity",
            f"{exp1.modularity:.3f} vs {exp2.modularity:.3f}",
            delta=f"{delta:.3f}" if abs(delta) > 0.001 else None,
            delta_color="normal",
        )

    with col6:
        delta = comparison["density_diff"]
        st.metric(
            "Density",
            f"{exp1.density:.3f} vs {exp2.density:.3f}",
            delta=f"{delta:.3f}" if abs(delta) > 0.001 else None,
            delta_color="normal",
        )

    # Notes comparison
    if exp1.notes or exp2.notes:
        st.subheader("Notes")
        col_n1, col_n2 = st.columns(2)
        with col_n1:
            st.write(f"**{exp1.id[:15]}...:**")
            st.write(exp1.notes or "_No notes_")
        with col_n2:
            st.write(f"**{exp2.id[:15]}...:**")
            st.write(exp2.notes or "_No notes_")
