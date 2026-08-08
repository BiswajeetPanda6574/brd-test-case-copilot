**Live demo:** [brd-test-case-copilot-jchfsugzf9nghpbxd8xz7d.streamlit.app](https://brd-test-case-copilot-jchfsugzf9nghpbxd8xz7d.streamlit.app/)

Live demo: brd-test-case-copilot-jchfsugzf9nghpbxd8xz7d.streamlit.app

BRD → Test Case Copilot

An AI-powered copilot that reads a Business Requirement Document (BRD) and automatically generates both positive and negative test cases for every requirement in seconds — turning a manual QA prep task into a near-instant automated one.

Why this project

This mirrors a real AI Engineering use case: building AI-driven business copilots that automate test case generation from BRDs. It combines document parsing, LLM-based requirement extraction, and structured generation into one end-to-end pipeline.

How it works
Read — parses a .docx, .pdf, or .txt BRD into plain text
Extract — prompts an LLM to pull out each distinct requirement as structured JSON (id, title, description)
Generate — sends all extracted requirements in a single batched prompt, and the LLM returns a Positive and a Negative test case for each one (preconditions, numbered steps, expected result) in one response
Deliver — displays results in a table in the app and lets the user download them as CSV
Tech stack
Python
Google Gemini API (2.5 Flash / 2.5 Flash-Lite — free tier, no credit card required)
Streamlit (front-end)
python-docx / pdfplumber (document parsing)
pandas (tabular output)
Running it
bash
pip install -r requirements.txt
export GEMINI_API_KEY=your_key_here
streamlit run app.py

Upload sample_brd.txt to try it immediately without sourcing your own document.

Project structure
brd-test-case-copilot/
├── app.py              # Streamlit UI
├── extractor.py         # BRD parsing + LLM extraction/generation logic
├── sample_brd.txt        # Sample BRD to test with
├── requirements.txt
└── .env.example
Next steps
Push generated test cases directly into a Google Sheet instead of CSV export
Deploy via a managed cloud AI service (e.g., Azure OpenAI or AWS Bedrock) to demonstrate cross-cloud deployment
Add a human-in-the-loop review/edit step before finalizing test cases
Future Improvements
Support non-functional requirements, business rules, and user roles as distinct BRD sections
Export to Excel/Jira-compatible formats in addition to CSV
Add a lightweight dashboard for reviewing and editing generated test cases before export
