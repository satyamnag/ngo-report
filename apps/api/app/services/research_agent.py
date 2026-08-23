"""OpenAI Agents SDK-powered research agent.

The agent has safe read-only tools:
  - fetch_url: SSRF-guarded public page fetch (respects the user's granted
    sources).
  - search_web: server-side web search (DuckDuckGo HTML).
It is given the user's source corpus (granted website/social URLs + uploaded
documents + org profile) and the strict report-content prompt, and returns the
content-plan JSON that is then merged into the project.

The OpenAI key is never exposed to the client; it is injected server-side.
"""

import json
import os
import re

from agents.decorators import tool

from ..config import settings


@tool
def fetch_url(url: str) -> str:
    """Fetch a public web page (read-only, SSRF-guarded) and return its text. Use for granted website/social pages."""
    from ..services.sources import FetchError, fetch_text

    try:
        return fetch_text(url)
    except FetchError as exc:
        return f"ERROR: {exc}"


@tool
def search_web(query: str) -> str:
    """Search the web for a query and return top results with snippets."""
    import html as html_lib
    import urllib.error
    import urllib.parse
    import urllib.request

    from ..services.sources import USER_AGENT

    url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            page = resp.read(2_000_000).decode("utf-8", errors="replace")
    except Exception as exc:
        return f"ERROR: search failed: {exc}"

    def _clean(s: str) -> str:
        return re.sub(r"\s+", " ", html_lib.unescape(re.sub(r"<[^>]+>", "", s))).strip()

    titles = re.findall(r'<a[^>]*class="result__a"[^>]*>(.*?)</a>', page)
    snippets = re.findall(r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>', page)
    out = []
    for i, (t, s) in enumerate(zip(titles, snippets), start=1):
        out.append(f"{i}. {_clean(t)}\n   {_clean(s)}")
    return "\n".join(out[:8]) or "No results found."


def _extract_json(text: str) -> dict:
    from ..services.ai_service import parse_agent_json

    return parse_agent_json(text)


def run_research_agent(
    org_profile: dict,
    corpus_text: str,
    template_schema: dict,
    user_prompt: str | None = None,
) -> dict:
    """Run the research agent and return the content plan JSON."""
    if not settings.openai_api_key:
        from ..services.ai_service import AiKeyMissingError

        raise AiKeyMissingError(
            "OPENAI_API_KEY is not configured on the backend. Add it to the "
            "server .env (OPENAI_API_KEY=...) and restart the API."
        )

    from agents import Agent, Runner, set_default_openai_key, set_tracing_disabled
    from agents.decorators import tool

    set_default_openai_key(settings.openai_api_key)
    set_tracing_disabled(True)

    from ..services.ai_service import load_prompt

    instructions = (
        load_prompt()
        + "\n\n## Research context\n"
        "You have read-only tools to fetch granted public pages and search the "
        "web. Use the source corpus in the user message as the primary evidence. "
        "Only add facts supported by the corpus, fetched pages, or search results. "
        "Never fabricate statistics, financials, names, or achievements."
    )

    agent = Agent(
        name="Annual Report Researcher",
        instructions=instructions,
        model=settings.openai_model,
        tools=[fetch_url, search_web],
    )

    user_message = json.dumps(
        {
            "org_profile": org_profile,
            "template_schema": template_schema or {},
            "source_corpus": (corpus_text or "")[: 120_000],
            "user_instructions": (user_prompt or "")[: 4000] or None,
        },
        indent=2,
    )

    # Run with one corrective retry if the agent returns invalid JSON.
    for attempt in range(2):
        result = Runner.run_sync(agent, user_message, max_turns=14)
        if not result.final_output or not result.final_output.strip():
            if attempt == 0:
                user_message += (
                    "\n\nYour previous response was empty. Return ONLY a strict "
                    "JSON object matching the schema exactly, no prose."
                )
                continue
            raise ValueError("Agent returned an empty response")
        try:
            return _extract_json(result.final_output)
        except ValueError:
            if attempt == 0:
                user_message += (
                    "\n\nYour previous output was not valid JSON. Return ONLY a "
                    "strict JSON object matching the schema exactly, no prose."
                )
                continue
            raise