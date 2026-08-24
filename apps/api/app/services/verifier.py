"""LLM-as-judge fact verification with confidence scoring.

Pattern from nihanthnaidu007/Research_Forge: after the report is generated,
extract the factual/numeric claims from the filled fields and have the LLM
judge each one against the gathered source corpus. Returns a verdict
(SUPPORTED / PARTIALLY_SUPPORTED / UNSUPPORTED) plus a 0-1 confidence score,
so the UI can flag which figures are verified vs. unverified. Purely
read-only and non-fatal: any failure returns {} (nothing changes).
"""

import json
import re

from ..config import settings
from ..services.ai_service import AiKeyMissingError, parse_agent_json

VERDICT_SCORES = {
    "SUPPORTED": 1.0,
    "PARTIALLY_SUPPORTED": 0.6,
    "UNSUPPORTED": 0.2,
}

JUDGE_SYSTEM = (
    "You are a meticulous fact-checking editor. You are given factual claims "
    "from an annual report and excerpts of the source material the report was "
    "built from. For EACH claim, judge whether the sources support it. "
    'Return ONLY a strict JSON object: {"verifications": [{"field": "...", '
    '"verdict": "SUPPORTED" or "PARTIALLY_SUPPORTED" or "UNSUPPORTED", '
    '"confidence": 0.0 to 1.0, "reasoning": "one short sentence"}]}. '
    "Be conservative: a claim not clearly present in the sources is "
    "UNSUPPORTED or PARTIALLY_SUPPORTED, never assume."
)


def _value_at(input_json: dict, path: str | None):
    if not path:
        return None
    node = input_json
    for key in path.split("."):
        if isinstance(node, dict) and node.get(key) not in (None, ""):
            node = node[key]
        else:
            return None
    return node


def _text_fields(schema_json: dict) -> list[dict]:
    fields = []
    for group in (schema_json or {}).get("fields", []):
        for field in group.get("fields", []):
            if field.get("type") == "image":
                continue
            fields.append(field)
    return fields


def verify_fields(input_json: dict, schema_json: dict, source_corpus: str) -> dict:
    """Return {field_name: {verdict, confidence, reasoning}} for verifiable
    (numeric / fact-bearing) fields. {} if there is nothing to verify or on
    any failure."""
    if not settings.openai_api_key:
        raise AiKeyMissingError(
            "OPENAI_API_KEY is not configured on the backend. Add it to the "
            "server .env (OPENAI_API_KEY=...) and restart the API."
        )

    claims = []
    for field in _text_fields(schema_json):
        name = field.get("name")
        path = field.get("path")
        value = _value_at(input_json, path)
        if value in (None, ""):
            continue
        text = str(value)
        # Only verify fields that carry numbers (figures/percentages/years).
        if field.get("type") == "number" or re.search(r"\d", text):
            claims.append({"field": name, "label": field.get("label") or name, "value": text})
    if not claims:
        return {}

    sources = (source_corpus or "").strip()[: 40_000]
    user = json.dumps(
        {"claims": [{"field": c["field"], "value": c["value"]} for c in claims],
         "sources": sources},
        indent=2,
    )

    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    completion = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": JUDGE_SYSTEM},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_object"},
        temperature=0.0,
    )
    content = completion.choices[0].message.content or "{}"
    try:
        parsed = parse_agent_json(content)
    except ValueError:
        return {}

    labels = {c["field"]: c["label"] for c in claims}
    result = {}
    for item in parsed.get("verifications") or []:
        field = item.get("field")
        if not field or field not in labels:
            continue
        verdict = str(item.get("verdict", "")).upper()
        if verdict not in VERDICT_SCORES:
            verdict = "UNSUPPORTED"
        confidence = item.get("confidence")
        try:
            confidence = round(float(confidence), 2) if confidence is not None else VERDICT_SCORES[verdict]
        except (TypeError, ValueError):
            confidence = VERDICT_SCORES[verdict]
        result[field] = {
            "label": labels[field],
            "verdict": verdict,
            "confidence": confidence,
            "reasoning": (item.get("reasoning") or "").strip()[:200],
        }
    return result