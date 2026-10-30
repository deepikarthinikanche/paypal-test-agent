"""AI analyzer: reads failed checks plus the store's source code (using Gemini)
and explains, in plain English, what went wrong and how to fix it."""
import json
import os

from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL = "gemini-2.5-flash"  # override with GEMINI_MODEL in .env

SYSTEM_PROMPT = (
    "You are a senior QA engineer reviewing a payment integration built on the PayPal API. "
    "You are given failed test checks and the source code of the store under test. "
    "Explain in plain English what went wrong, find the likely cause in the code, and "
    "suggest a fix. Only claim things supported by the test results and the code. "
    "Group failures that share one root cause into a single finding. "
    "Reply with JSON only."
)

JSON_SHAPE = """{
  "summary": "one or two sentences for a non-technical reader",
  "findings": [
    {
      "check_ids": ["ids of the failed checks this finding explains"],
      "title": "short title",
      "severity": "high | medium | low",
      "what_happened": "plain English: expected vs actual",
      "likely_cause": "the root cause, pointing at the code",
      "suggested_fix": "what to change, in plain English",
      "code_fix": "a short corrected code snippet"
    }
  ]
}"""


def call_model(prompt):
    """Send the prompt to Gemini and return the raw text of the reply."""
    from google import genai
    from google.genai import types

    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError(
            "Missing GEMINI_API_KEY. Add it to your .env file (get one at aistudio.google.com)."
        )
    client = genai.Client(api_key=key)
    response = client.models.generate_content(
        model=os.getenv("GEMINI_MODEL", DEFAULT_MODEL),
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            temperature=0.2,
        ),
    )
    return response.text


def build_prompt(failed_checks, source_code):
    return (
        "FAILED CHECKS (JSON):\n"
        + json.dumps(failed_checks, indent=2)
        + "\n\nSOURCE CODE OF THE STORE UNDER TEST:\n"
        + source_code
        + "\n\nReturn JSON in exactly this shape:\n"
        + JSON_SHAPE
    )


def parse_reply(text):
    """Parse the model reply, tolerating markdown code fences."""
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        text = text.rsplit("```", 1)[0]
    data = json.loads(text)
    if not isinstance(data, dict) or not isinstance(data.get("findings"), list):
        raise ValueError("Model reply is missing a 'findings' list")
    return data


def explain_failures(failed_checks, source_code, call=call_model):
    reply = call(build_prompt(failed_checks, source_code))
    return parse_reply(reply)


def render_markdown(analysis, run_info):
    lines = [
        "# PayPal Test Agent: Analysis Report",
        "",
        f"Run time: {run_info.get('run_at', 'unknown')}  ",
        f"Checks passed: {run_info.get('passed')} of {run_info.get('total')}",
        "",
        "## Summary",
        "",
        analysis.get("summary", ""),
        "",
    ]
    for i, f in enumerate(analysis.get("findings", []), 1):
        lines += [
            f"## Finding {i}: {f.get('title', 'Untitled')}",
            "",
            f"**Severity:** {f.get('severity', 'unknown')}  ",
            f"**Failed checks:** {', '.join(f.get('check_ids', []))}",
            "",
            f"**What happened:** {f.get('what_happened', '')}",
            "",
            f"**Likely cause:** {f.get('likely_cause', '')}",
            "",
            f"**Suggested fix:** {f.get('suggested_fix', '')}",
            "",
        ]
        if f.get("code_fix"):
            lines += ["```python", f["code_fix"].strip(), "```", ""]
    return "\n".join(lines)
