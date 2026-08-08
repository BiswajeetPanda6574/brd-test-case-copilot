"""
Streamlit front-end for the BRD -> Test Case Copilot.

Run with:
    streamlit run app.py

Requires a GEMINI_API_KEY environment variable (see .env.example).
"""

import os

import streamlit as st
from google import genai
from google.genai import types

from extractor import read_brd, extract_requirements, generate_test_cases, to_dataframe

st.set_page_config(page_title="BRD -> Test Case Copilot", layout="wide")

st.title("BRD -> Test Case Copilot")
st.write(
    "Upload a Business Requirement Document (.docx, .pdf, or .txt). "
    "The copilot extracts each requirement and generates a structured test case for it."
)

api_key = os.environ.get("GEMINI_API_KEY", "")
if not api_key:
    st.warning("Set the GEMINI_API_KEY environment variable before running (see .env.example).")

model_choice = st.selectbox(
    "Model",
    options=["gemini-flash-latest", "gemini-flash-lite-latest"],
    help="Flash gives higher-quality test cases; Flash-Lite is faster and cheaper for quick demos.",
)

uploaded_file = st.file_uploader("Upload BRD", type=["docx", "pdf", "txt"])

if uploaded_file and st.button("Generate Test Cases", type="primary", disabled=not api_key):
    client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=30000))

    with st.spinner("Reading document..."):
        brd_text = read_brd(file_bytes=uploaded_file.read(), filename=uploaded_file.name)

    with st.expander("Extracted BRD text (for reference)"):
        st.text(brd_text)

    with st.spinner("Extracting requirements..."):
        requirements = extract_requirements(brd_text, client, model=model_choice)

    st.success(f"Extracted {len(requirements)} requirements.")
    with st.expander("Requirements"):
        for r in requirements:
            st.markdown(f"**{r['id']} — {r['title']}**  \n{r['description']}")

    requirement_count = len(requirements)
    st.info(
        f"Generating test cases for all {requirement_count} requirements in a single API call "
        f"(2 calls total for this run, vs. {requirement_count + 1} in the earlier per-requirement version)."
    )
    if requirement_count > 30:
        st.warning(
            f"This BRD has {requirement_count} requirements. Very large batches can occasionally get cut off "
            "in a single response — if the output below looks incomplete, try a smaller BRD or split it into sections."
        )

    with st.spinner("Generating test cases..."):
        test_cases = generate_test_cases(requirements, client, model=model_choice)

    df = to_dataframe(test_cases)
    st.subheader("Generated Test Cases")
    st.dataframe(df, use_container_width=True)

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download as CSV",
        data=csv,
        file_name="generated_test_cases.csv",
        mime="text/csv",
    )
