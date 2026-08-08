"""
Core logic for the BRD -> Test Case Copilot.

Handles:
  - reading BRD content from .docx, .pdf, or .txt
  - extracting structured requirements from the BRD text using an LLM
  - generating structured test cases for each requirement
"""

import json
import re
import time
from typing import List


# ---------------------------------------------------------------------------
# 1. Reading the BRD
# ---------------------------------------------------------------------------

def read_brd(file_path: str = None, file_bytes: bytes = None, filename: str = None) -> str:
    """
    Reads a BRD file and returns its plain text content.
    Accepts either a path on disk, or raw bytes + filename (for Streamlit uploads).
    Supports .docx, .pdf, and .txt.
    """
    if filename is None:
        filename = file_path

    ext = filename.lower().rsplit(".", 1)[-1]

    if ext == "txt":
        if file_bytes is not None:
            return file_bytes.decode("utf-8", errors="ignore")
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    if ext == "docx":
        import docx
        import io
        source = io.BytesIO(file_bytes) if file_bytes is not None else file_path
        doc = docx.Document(source)
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())

    if ext == "pdf":
        import pdfplumber
        import io
        source = io.BytesIO(file_bytes) if file_bytes is not None else file_path
        text_parts = []
        with pdfplumber.open(source) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return "\n".join(text_parts)

    raise ValueError(f"Unsupported file type: .{ext}. Use .docx, .pdf, or .txt.")


# ---------------------------------------------------------------------------
# 2. Extracting requirements
# ---------------------------------------------------------------------------

def _parse_json_block(raw_text: str):
    """Strips markdown code fences (if the model adds them) and parses JSON."""
    cleaned = re.sub(r"^```(json)?|```$", "", raw_text.strip(), flags=re.MULTILINE).strip()
    return json.loads(cleaned)


def _call_with_retry(client, model: str, prompt: str, max_retries: int = 3):
    """
    Calls the Gemini API, automatically retrying with a longer wait if the
    free-tier rate limit (HTTP 429) is hit. Re-raises any other error immediately.
    """
    delay = 15
    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content(model=model, contents=prompt)
            return response.text
        except Exception as e:
            is_rate_limit = "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e)
            if is_rate_limit and attempt < max_retries:
                time.sleep(delay)
                delay += 10  # back off a little more each retry
                continue
            raise


EXTRACTION_PROMPT = """You are a business analyst assistant. Read the Business Requirement Document (BRD) text below and extract each distinct functional or business requirement.

Return ONLY a JSON array, no other text, no markdown fences. Each element must have this shape:
{{
  "id": "REQ-01",
  "title": "short title",
  "description": "one to two sentence description of what the system must do"
}}

BRD TEXT:
---
{brd_text}
---

Return only the JSON array."""


def extract_requirements(brd_text: str, client, model: str = "gemini-flash-latest") -> List[dict]:
    """Calls the LLM to pull structured requirements out of raw BRD text."""
    raw = _call_with_retry(client, model, EXTRACTION_PROMPT.format(brd_text=brd_text))
    return _parse_json_block(raw)


# ---------------------------------------------------------------------------
# 3. Generating test cases
# ---------------------------------------------------------------------------

BATCH_TEST_CASE_PROMPT = """You are a QA engineer. Write one detailed test case for each requirement listed below.

Requirements (JSON array):
{requirements_json}

Return ONLY a JSON array, no other text, no markdown fences. Return exactly one test case per requirement,
in the same order as the requirements above, each shaped exactly like this:
{{
  "requirement_id": "<the matching requirement's id>",
  "title": "short test case title",
  "preconditions": "state required before the test",
  "steps": ["step 1", "step 2", "step 3"],
  "expected_result": "what should happen if the requirement is correctly implemented"
}}"""


def generate_test_cases(requirements: List[dict], client, model: str = "gemini-flash-latest", progress_callback=None) -> List[dict]:
    """
    Generates test cases for ALL requirements in a single batched API call, instead of
    one call per requirement. This cuts a run from N+1 API calls down to just 2 total
    (1 to extract requirements, 1 to generate every test case), which avoids the
    free tier's per-minute and per-day rate limits for typical BRD sizes and finishes
    in seconds instead of minutes.
    progress_callback, if given, is called once as progress_callback(1, 1) since the
    whole batch completes in one step (kept for interface compatibility with callers).
    """
    requirements_json = json.dumps(requirements, indent=2)
    raw = _call_with_retry(client, model, BATCH_TEST_CASE_PROMPT.format(requirements_json=requirements_json))
    test_cases = _parse_json_block(raw)
    for i, tc in enumerate(test_cases, start=1):
        tc["test_case_id"] = f"TC-{i:02d}"
    if progress_callback:
        progress_callback(1, 1)
    return test_cases


# ---------------------------------------------------------------------------
# 4. Formatting output
# ---------------------------------------------------------------------------

def to_dataframe(test_cases: List[dict]):
    """Flattens the list of test case dicts (with a list-type 'steps' field) into a table."""
    import pandas as pd

    rows = []
    for tc in test_cases:
        rows.append({
            "Test Case ID": tc.get("test_case_id", ""),
            "Requirement ID": tc.get("requirement_id", ""),
            "Title": tc.get("title", ""),
            "Preconditions": tc.get("preconditions", ""),
            "Steps": "\n".join(f"{i + 1}. {s}" for i, s in enumerate(tc.get("steps", []))),
            "Expected Result": tc.get("expected_result", ""),
        })
    return pd.DataFrame(rows)
