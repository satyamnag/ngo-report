"""OpenAI content-plan generation for the publication-style annual report.

Builds the org profile, sends it with the strict agent prompt (verified against
the official OpenAI Python SDK docs), and returns the JSON content plan. The
plan is then merged back into the project's input_json to auto-fill the report.
"""

import json
import re
from pathlib import Path

from ..config import settings

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "report_content_generator.md"


class AiKeyMissingError(RuntimeError):
    """Raised when no OpenAI API key is configured."""


def load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def input_json_to_profile(input_json: dict) -> dict:
    """Flatten the form's dotted input_json into the org_profile shape the
    agent prompt expects. Missing/empty values are omitted."""
    n = input_json.get
    impact = input_json.get("impact") or {}
    financial = input_json.get("financial") or {}

    def _num(value):
        if value in (None, ""):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return str(value)

    profile = {
        "org_name": n("org_name"),
        "report_year": n("report_year"),
        "tagline": n("tagline"),
        "report_type": n("report_type"),
        "about_report": n("about_report"),
        "mission": n("mission_statement"),
        "leader": {"name": n("leader_name"), "title": n("leader_title")},
        "opening_quote": {"text": n("opening_quote"), "author": n("opening_quote_author")},
        "stats": {
            "beneficiaries": _num(impact.get("beneficiaries")),
            "communities": _num(impact.get("communities")),
            "volunteers": _num(impact.get("volunteers")),
            "districts": _num(impact.get("districts")),
        },
        "impact": {
            "summary": n("impact_summary"),
            "quote": {"text": n("impact_quote"), "author": n("impact_quote_author")},
        },
        "programmes": [
            {
                "name": n(f"program_{i}_name"),
                "description": n(f"program_{i}_desc"),
            }
            for i in range(1, 5)
        ],
        "milestones": [
            {"year": n(f"milestone_{i}_year"), "text": n(f"milestone_{i}_text")}
            for i in range(1, 6)
        ],
        "financials": {
            "summary": n("financial_summary"),
            "programmes_amount": financial.get("programmes"),
            "programmes_share": financial.get("programmes_share"),
            "admin_amount": financial.get("admin"),
            "admin_share": financial.get("admin_share"),
            "total": financial.get("total"),
        },
        "donors": {
            "acknowledgment": n("donors_ack"),
            "quote": {"text": n("donor_quote"), "author": n("donor_quote_author")},
        },
        "goals": n("future_goals"),
        "closing_statement": n("closing_statement"),
        "contact": {
            "address": n("contact_address"),
            "phone": n("contact_phone"),
            "email": n("contact_email"),
            "website": n("contact_website"),
            "social": n("contact_social"),
        },
    }
    # Drop null/empty values so the prompt sees "no data".
    return {k: v for k, v in profile.items() if v not in (None, "")}


def _extract_json(text: str) -> dict:
    """Parse model output as JSON, tolerating markdown fences and common
    lenient-JSON mistakes (unquoted keys, trailing commas) via json5."""
    return parse_agent_json(text)


def parse_agent_json(text: str) -> dict:
    """Robustly parse an agent's JSON output.

    Order: strict JSON -> balanced-brace extraction (strict + json5) -> json5
    on the whole string. Raises ValueError only if nothing parses.
    """
    import json as _json

    cleaned = (text or "").strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1).strip()

    def _strict(s: str):
        try:
            return _json.loads(s)
        except Exception:
            return None

    def _lenient(s: str):
        try:
            import json5

            return json5.loads(s)
        except Exception:
            return None

    d = _strict(cleaned)
    if d is not None:
        return d

    # Try each substring starting at an opening brace and ending at the last
    # closing brace (handles leading prose or stray characters).
    candidates = []
    for idx, ch in enumerate(cleaned):
        if ch == "{":
            candidates.append(cleaned[idx:])
    for candidate in candidates:
        d = _strict(candidate)
        if d is not None:
            return d
        d = _lenient(candidate)
        if d is not None:
            return d

    d = _lenient(cleaned)
    if d is not None:
        return d

    raise ValueError("Agent returned invalid JSON")


def generate_content_plan(org_profile: dict, template_schema: dict) -> dict:
    """Call OpenAI with the agent prompt + org profile, return the plan JSON."""
    if not settings.openai_api_key:
        raise AiKeyMissingError(
            "OPENAI_API_KEY is not configured on the backend. Add it to the "
            "server .env (OPENAI_API_KEY=...) and restart the API."
        )

    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    system = load_prompt()
    user = json.dumps(
        {"org_profile": org_profile, "template_schema": template_schema or {}},
        indent=2,
    )

    completion = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_object"},
        temperature=0.7,
    )
    content = completion.choices[0].message.content
    if not content:
        raise ValueError("OpenAI returned an empty response")
    return _extract_json(content)


# Narrative fields the AI may rewrite/improve (factual fields are preserved).
_NARRATIVE_MAP = {
    "foreword": "foreword",
    "quote": ("opening_quote", "opening_quote_author"),
    "overview": ("about_intro", "overview_narrative"),
    "impact": ("impact_summary", "impact_quote", "impact_quote_author"),
    "programs": "programs_intro",
    "milestones": "milestones_intro",
    "financials": "financial_summary",
    "donors": ("donors_ack", "donor_quote", "donor_quote_author"),
    "goals": "future_goals",
    "closing": "closing_statement",
}


def _paragraphs(page: dict) -> list[str]:
    return [p for p in (page.get("paragraphs") or []) if p]


def _quotes(page: dict) -> list[dict]:
    return [q for q in (page.get("quotes") or []) if q and q.get("text")]


def merge_plan(input_json: dict, plan: dict) -> dict:
    """Fold the AI content plan into project.input_json.

    Narrative fields are overwritten with the AI text; factual fields (stats,
    financial amounts, milestone years, programme names) are only filled in
    when currently empty so no real data is ever replaced.
    """
    merged = dict(input_json)
    pages = plan.get("pages") or []

    def _set(path: str, value) -> None:
        if value in (None, ""):
            return
        keys = path.split(".")
        node = merged
        for key in keys[:-1]:
            node = node.setdefault(key, {})
        node[keys[-1]] = value

    def _set_if_empty(path: str, value) -> None:
        keys = path.split(".")
        node = merged
        for key in keys[:-1]:
            node = node.setdefault(key, {})
        current = node.get(keys[-1])
        if current in (None, ""):
            node[keys[-1]] = value

    for page in pages:
        key = page.get("section_key")
        targets = _NARRATIVE_MAP.get(key)
        if not targets:
            continue

        text = "\n\n".join(_paragraphs(page))
        if isinstance(targets, str):
            _set(targets, text)
            continue

        # (primary, quote, author) style mapping
        if key == "quote" and _quotes(page):
            _set(targets[0], _quotes(page)[0].get("text"))
            _set(targets[1], _quotes(page)[0].get("author"))
        elif key in ("impact", "donors"):
            _set(targets[0], text)
            quotes = _quotes(page)
            if quotes:
                _set(targets[1], quotes[0].get("text"))
                _set(targets[2], quotes[0].get("author"))
        elif key == "overview":
            paragraphs = _paragraphs(page)
            if paragraphs:
                _set(targets[0], paragraphs[0])
                _set(targets[1], "\n\n".join(paragraphs[1:]))

        # Fill empty stats from the plan (never overwrite user numbers).
        if key == "overview" and page.get("stats"):
            for stat in page["stats"]:
                label_to_path = {
                    "Beneficiaries served": "impact.beneficiaries",
                    "Communities reached": "impact.communities",
                    "Volunteers engaged": "impact.volunteers",
                    "Districts served": "impact.districts",
                }
                path = label_to_path.get(str(stat.get("label")))
                if path and stat.get("value") is not None:
                    _set_if_empty(path, stat.get("value"))

    return merged