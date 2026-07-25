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

TEST_CASE_PROMPT = """You are a QA engineer. Write one detailed test case for the requirement below.

Requirement ID: {req_id}
Requirement title: {title}
Requirement description: {description}

Return ONLY a JSON object, no other text, no markdown fences, in this shape:
{{
  "test_case_id": "TC-01",
  "requirement_id": "{req_id}",
  "title": "short test case title",
  "preconditions": "state required before the test",
  "steps": ["step 1", "step 2", "step 3"],
  "expected_result": "what should happen if the requirement is correctly implemented"
}}"""


def generate_test_case(requirement: dict, client, index: int, model: str = "gemini-flash-latest") -> dict:
    """Calls the LLM to generate one structured test case for one requirement."""
    prompt = TEST_CASE_PROMPT.format(
        req_id=requirement["id"],
        title=requirement["title"],
        description=requirement["description"],
    )
    raw = _call_with_retry(client, model, prompt)
    test_case = _parse_json_block(raw)
    test_case["test_case_id"] = f"TC-{index:02d}"
    return test_case


def generate_test_cases(requirements: List[dict], client, model: str = "gemini-flash-latest", progress_callback=None) -> List[dict]:
    """
    Generates one test case per requirement, in order.
    Pauses between calls to stay under the free tier's 5-requests-per-minute limit.
    If progress_callback is given, it's called as progress_callback(current, total) after each requirement.
    """
    test_cases = []
    total = len(requirements)
    for i, req in enumerate(requirements, start=1):
        tc = generate_test_case(req, client, i, model=model)
        test_cases.append(tc)
        if progress_callback:
            progress_callback(i, total)
        if i < total:
            time.sleep(13)  # free tier allows 5 requests/minute; this keeps every call under that
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
