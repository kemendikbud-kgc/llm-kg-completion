"""Knowledge Graph Findings — Stakeholder demo page (read-only)."""

import streamlit as st

from src.graph import get_driver, get_graph_stats
from src.queries import QUERIES

st.set_page_config(page_title="KG Findings Demo", layout="wide")

# ── Header ────────────────────────────────────────────────────────────────────
st.title("Knowledge Graph Findings")
st.caption(
    "Read-only dashboard for thesis committee · "
    "Analisis Kurikulum berbasis Knowledge Graph"
)

# ── Neo4j connection ──────────────────────────────────────────────────────────
_neo4j_error: str | None = None
try:
    driver = get_driver()
    # Verify connectivity with a lightweight probe
    with driver.session() as _s:
        _s.run("RETURN 1").consume()
except Exception as e:
    _neo4j_error = str(e)
    driver = None  # type: ignore[assignment]

if _neo4j_error:
    st.warning(
        f"Neo4j is unreachable — showing empty data. Error: `{_neo4j_error}`\n\n"
        "Check your `.env` credentials and network, then reload the page."
    )

# ── Section A — Key Numbers ───────────────────────────────────────────────────
st.subheader("A · Key Numbers")

stats = get_graph_stats(driver) if driver else {
    "subjects": 0, "documents": 0, "babs": 0,
    "konsep": 0, "sub_konsep": 0,
    "analogous_rels": 0, "prereq_rels": 0, "supports_rels": 0,
}

cols = st.columns(8)
metrics = [
    ("MataPelajaran", stats["subjects"]),
    ("Documents", stats["documents"]),
    ("Bab", stats["babs"]),
    ("Konsep", stats["konsep"]),
    ("SubKonsep", stats["sub_konsep"]),
    ("analogousTo", stats["analogous_rels"]),
    ("isPrerequisiteOf", stats["prereq_rels"]),
    ("supports", stats["supports_rels"]),
]
for col, (label, value) in zip(cols, metrics):
    col.metric(label, value)

st.divider()

# ── Section B — Cross-Subject Analogies ──────────────────────────────────────
st.subheader("B · Cross-Subject Analogies  *(Flagship Finding)*")
st.caption(
    "These concept pairs share the same underlying pattern across different subjects "
    "— evidence of siloed curriculum design."
)

cross_q = next(q for q in QUERIES if q["title"] == "Cross-Subject Analogies")

try:
    with driver.session() as session:
        rows = [
            dict(r)
            for r in session.run(cross_q["cypher"])
        ]
except Exception as e:
    rows = []
    st.warning(f"Query error: {e}")

if rows:
    import pandas as pd

    df = pd.DataFrame(rows, columns=["subject_a", "konsep_a", "konsep_b", "subject_b"])
    df.columns = ["Subject A", "Konsep A", "Konsep B", "Subject B"]
    st.dataframe(df, use_container_width=True)

    # Mini graph with streamlit-agraph
    try:
        from streamlit_agraph import agraph, Node, Edge, Config

        # Colour by subject
        subject_colors: dict[str, str] = {}
        palette = ["#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B3"]
        subjects = list({r["Subject A"] for r in df.to_dict("records")} |
                        {r["Subject B"] for r in df.to_dict("records")})
        for i, s in enumerate(subjects):
            subject_colors[s] = palette[i % len(palette)]

        nodes: list[Node] = []
        edges: list[Edge] = []
        seen_nodes: set[str] = set()

        for row in df.to_dict("records"):
            for konsep, subject in [
                (row["Konsep A"], row["Subject A"]),
                (row["Konsep B"], row["Subject B"]),
            ]:
                if konsep not in seen_nodes:
                    seen_nodes.add(konsep)
                    nodes.append(
                        Node(
                            id=konsep,
                            label=konsep[:30],
                            title=f"{konsep}\n({subject})",
                            color=subject_colors.get(subject, "#999"),
                            size=20,
                        )
                    )
            edges.append(
                Edge(
                    source=row["Konsep A"],
                    target=row["Konsep B"],
                    label="analogousTo",
                    color="#aaa",
                )
            )

        cfg = Config(width=900, height=380, directed=False, physics=True, hierarchical=False)
        agraph(nodes=nodes, edges=edges, config=cfg)

        # Legend
        legend_cols = st.columns(len(subject_colors))
        for col, (subj, color) in zip(legend_cols, subject_colors.items()):
            col.markdown(
                f'<span style="background:{color};padding:2px 8px;border-radius:4px;'
                f'color:white;font-size:0.85em">{subj}</span>',
                unsafe_allow_html=True,
            )
    except ImportError:
        st.info("Install `streamlit-agraph` to see the graph visualisation.")
else:
    st.info(
        "No cross-subject analogousTo relationships found yet. "
        "Run Step 5b (Classify Relationships) first."
    )

st.divider()

# ── Section C — Prerequisite Explorer ────────────────────────────────────────
st.subheader("C · Prerequisite Explorer")

try:
    with driver.session() as session:
        all_konsep = [
            r["name"]
            for r in session.run("MATCH (k:Konsep) RETURN k.name AS name ORDER BY k.name")
        ]
except Exception as e:
    all_konsep = []
    st.warning(f"Could not load Konsep list: {e}")

if all_konsep:
    selected_konsep = st.selectbox("Select a Konsep to explore its prerequisites:", all_konsep)

    prereq_q = next(q for q in QUERIES if q["title"] == "Prerequisite Chains")
    # Replace parameterised query with literal for session.run
    prereq_cypher = """\
MATCH path = (k:Konsep {name: $name})-[:isPrerequisiteOf*1..4]->(downstream:Konsep)
WITH nodes(path) AS chain
UNWIND range(0, size(chain)-2) AS i
RETURN chain[i].name AS from_konsep, chain[i+1].name AS to_konsep"""

    try:
        with driver.session() as session:
            prereq_rows = [
                dict(r)
                for r in session.run(prereq_cypher, name=selected_konsep)
            ]
    except Exception as e:
        prereq_rows = []
        st.warning(f"Query error: {e}")

    if prereq_rows:
        import pandas as pd

        prereq_df = pd.DataFrame(prereq_rows)
        prereq_df.columns = ["From Konsep", "To Konsep (downstream)"]
        st.dataframe(prereq_df, use_container_width=True)

        try:
            from streamlit_agraph import agraph, Node, Edge, Config

            nodes = []
            edges = []
            seen: set[str] = set()
            for row in prereq_rows:
                for name in [row["From Konsep"], row["To Konsep (downstream)"]]:
                    if name not in seen:
                        seen.add(name)
                        nodes.append(Node(id=name, label=name[:30], size=18))
                edges.append(
                    Edge(
                        source=row["From Konsep"],
                        target=row["To Konsep (downstream)"],
                        label="isPrerequisiteOf",
                    )
                )
            cfg = Config(width=900, height=320, directed=True, physics=True, hierarchical=False)
            agraph(nodes=nodes, edges=edges, config=cfg)
        except ImportError:
            pass
    else:
        st.info(f"No outgoing prerequisite chains found for **{selected_konsep}**.")
else:
    st.info("No Konsep in graph yet.")

st.divider()

# ── Section D — Neo4j Bloom Search Phrases ─────────────────────────────────────
st.subheader("D · Neo4j Bloom Search Phrases")
st.info(
    "**How to use:** Open Neo4j Bloom → click **Search** → **Search Phrases** → **Add**. "
    "Paste the phrase name and the Cypher query below."
)

categories = sorted({q["category"] for q in QUERIES})
for cat in categories:
    cat_queries = [q for q in QUERIES if q["category"] == cat]
    st.markdown(f"### {cat}")
    for q in cat_queries:
        with st.expander(f"**{q['title']}** — _{q['description']}_"):
            st.markdown(f"**Bloom Search Phrase name:** `{q['bloom_phrase']}`")
            st.code(q["cypher"], language="cypher")

if driver:
    driver.close()
