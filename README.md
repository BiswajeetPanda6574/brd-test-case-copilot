**Live demo:** [(https://brd-test-case-copilot-jchfsugzf9nghpbxd8xz7d.streamlit.app/)].streamlit.app

# BRD → Test Case Copilot

An AI-powered copilot that reads a Business Requirement Document (BRD) and automatically generates structured test cases for each requirement — turning a manual QA prep task into a few minutes of automated work.

## Why this project

This mirrors a real AI Engineering use case: building AI-driven business copilots that automate test case generation from BRDs. It combines document parsing, LLM-based requirement extraction, and structured generation into one end-to-end pipeline.

## How it works

1. **Read** — parses a `.docx`, `.pdf`, or `.txt` BRD into plain text
2. **Extract** — prompts an LLM to pull out each distinct requirement as structured JSON (id, title, description)
3. **Generate** — for each requirement, prompts the LLM to produce a full test case: preconditions, numbered steps, and expected result
4. **Deliver** — displays results in a table in the app and lets the user download them as CSV

## Tech stack

- Python
- Google Gemini API (2.5 Flash / 2.5 Flash-Lite — free tier, no credit card required)
- Streamlit (front-end)
- python-docx / pdfplumber (document parsing)
- pandas (tabular output)

## Running it

```bash
pip install -r requirements.txt
export GEMINI_API_KEY=your_key_here
streamlit run app.py
```

Upload `sample_brd.txt` to try it immediately without sourcing your own document.

## Project structure

```
brd-test-case-copilot/
├── app.py              # Streamlit UI
├── extractor.py         # BRD parsing + LLM extraction/generation logic
├── sample_brd.txt        # Sample BRD to test with
├── requirements.txt
└── .env.example
```

## Next steps

- Push generated test cases directly into a Google Sheet instead of CSV export
- Deploy via a managed cloud AI service (e.g., Azure OpenAI or AWS Bedrock) to demonstrate cross-cloud deployment
- Add a human-in-the-loop review/edit step before finalizing test cases
