# Data Safety & Legal Alignment

This document records how the research agent gathers information and how that
process is kept safe for the platform **and** for the user/customer, and aligned
with legal rules so there is no legal threat to the platform.

## 1. What the agent gathers

The agent (OpenAI Agents SDK) is allowed to use **only**:

1. The organization's own facts entered in the report form (`org_profile`).
2. The **source corpus the user explicitly grants**: their official website and
   their Facebook / Instagram / X (Twitter) / LinkedIn / YouTube pages, fetched
   **read-only** as public pages.
3. The **research documents the user uploads** (txt, Word, Excel, PowerPoint,
   PDF, images) — stored on the platform's own server.
4. Public web search results **about the organization itself**, used only to
   corroborate or complete the organization's own public information.

Everything else is out of scope. All source fields and document uploads are
**optional**; the agent works with whatever the user provides.

## 2. How it is kept safe (technical)

- **Read-only, SSRF-guarded fetching.** Source fetching is limited to
  `http/https`, resolves and validates the target IP (private, loopback,
  link-local, multicast, and reserved ranges are blocked), is size-capped
  (2 MB) and time-limited (15 s), and uses a descriptive user agent. Fetching
  never sends credentials and never writes anything.
- **User-granted only.** No source is fetched until the user enters its URL.
- **Your own server.** Uploaded documents and fetched text are stored on the
  platform's own infrastructure (object storage + PostgreSQL) and scoped to the
  project. They are never sent to third parties except the OpenAI API for the
  purpose of generating the report content.
- **Deletion.** Deleting a report deletes its documents, fetched text, and
  generated files.
- **Secrets.** The OpenAI API key is server-side only; it is never sent to the
  browser.
- **Least data.** Only the minimum text needed to write the report is sent to
  the model, and it is scoped to what the user granted.

## 3. How it is kept legal (prompt-enforced, non-negotiable)

The agent prompt (`apps/api/prompts/report_content_generator.md`) enforces:

1. **Permission boundary** — use only content the user granted; never read or
   copy third-party content outside that boundary.
2. **No verbatim reproduction** — all sourced text is paraphrased; copyrighted
   text is never reproduced verbatim.
3. **No personal/private data** — no individuals' private details unless the
   user explicitly provided them.
4. **No fabricated endorsements or facts** — no invented donors, awards,
   partnerships, stats, or financials; uncertain facts are marked
   "to be provided" or left `null`.
5. **Ownership** — generated content belongs to the user's NGO; no third-party
   brands are injected.
6. **If in doubt, leave it out** — unverifiable claims are omitted.

Because the platform only reads the user's own public content, only sends the
minimum required data to OpenAI, never redistributes third-party material, and
never fabricates facts, the process stays within the user's consent and
applicable content/licensing rules.

## 4. User-facing notice

Every page that touches the user's data shows:

> **Your data is 100% safe.** We only read the public pages you explicitly
> grant, your documents stay on your own server and are never shared, and
> everything is deleted if you delete the report.