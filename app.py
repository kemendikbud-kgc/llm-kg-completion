"""Streamlit app - main entry point."""

import streamlit as st
import json

from src.ingestion import extract_text_from_pdf
from src.extraction import extract_topics
from src.graph import get_driver, insert_topics

st.set_page_config(page_title="KG Completion Pipeline", layout="wide")
st.title("LLM-Assisted Knowledge Graph Completion")

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
    if st.button("Run Extraction"):
        with st.spinner("Calling LLM..."):
            result = extract_topics(raw_text)
        st.session_state["extracted"] = result

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
