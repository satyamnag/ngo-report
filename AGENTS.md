# AGENTS.md

# MANDATORY FIRST ACTION — READ THIS FILE BEFORE ANYTHING

Before doing ANYTHING and EVERYTHING — before any investigation, any question,
any command, any code change, any commit, any configuration, any debugging, or
any engineering decision of any kind — the agent MUST first read this AGENTS.md
file completely and in full, and strictly follow every instruction it contains.

This obligation is ABSOLUTE / MANDATORY / NON-NEGOTIABLE / ZERO EXCEPTIONS and
applies to EVERY single action, without exception, every time.

# Enterprise Autonomous Engineering Excellence & Zero-Assumption Development Policy

## Version: 5.0

## Enforcement Level

ABSOLUTE / MANDATORY / NON-NEGOTIABLE / ZERO EXCEPTIONS

------------------------------------------------------------------------

# Supreme Engineering Commandment

## NEVER GUESS.

## NEVER ASSUME.

## NEVER IMPLEMENT FROM MEMORY.

## NEVER TRUST UNVERIFIED INFORMATION.

Every engineering action MUST follow:

Evidence → Official Documentation Verification → System Understanding →
Risk Analysis → Planning → Small Atomic Implementation → Testing →
Security Validation → Review → Documentation → Commit → Continue

No step may be skipped.

------------------------------------------------------------------------

# Engineering Priority Hierarchy

1.  Correctness
2.  Security
3.  Reliability
4.  Maintainability
5.  Compatibility
6.  Scalability
7.  Performance
8.  Developer Experience
9.  Speed

Fast but unsafe solutions are forbidden.

------------------------------------------------------------------------

# Official Documentation Is The Absolute Source Of Truth

Before ANY:

-   Code change
-   Debugging
-   Bug fix
-   Dependency change
-   Configuration change
-   API usage
-   SDK usage
-   Database change
-   Cloud change
-   Infrastructure change
-   Security change
-   Architecture change
-   Migration
-   Deployment change

The agent MUST verify official documentation first.

------------------------------------------------------------------------

# Approved Official Documentation MCP Sources

The agent MUST use appropriate official documentation MCP sources:

-   context7
-   ref
-   gitmcp
-   deepwiki
-   docker
-   freeweb
-   exa
-   terraform
-   aws-knowledge
-   markitdown
-   pdf-reader
-   pdf-mcp
-   huggingface
-   repomix
-   godot
-   clickhouse
-   excel
-   youtube-transcript
-   duckduckgo
-   everything
-   selenium
-   puppeteer
-   browserbase
-   memory
-   context-awesome
-   flux
-   sequential-thinking
-   appium-mcp
-   scrcpy-mcp
-   agent-device
-   uiautomator2-mcp

------------------------------------------------------------------------

# Android Mobile App Testing (Mandatory MCP Servers)

For ANY Android app verification, UI testing, device interaction, screenshot
capture, or end-to-end testing, the agent MUST use the dedicated Android MCP
servers below instead of ad-hoc `adb shell` / `uiautomator dump` commands,
whenever the servers are available and appropriate:

-   **appium-mcp** — official Appium-team MCP server (Android + iOS). Use for
    Appium-driven automation: sessions, element finding, gestures, screenshots,
    device control.
-   **scrcpy-mcp** — Android device control + vision via ADB and scrcpy. Use
    for screen capture, tap/swipe/type input, app launch, UI element finding,
    file transfer, and shell commands on the connected device/emulator.
-   **agent-device** — Callstack's mobile automation CLI + MCP server (iOS,
    Android, HarmonyOS). Use for app install/launch, UI interaction, snapshots,
    and verification workflows.
-   **uiautomator2-mcp** — Android automation via uiautomator2
    (tap/swipe/type/screenshot/app management). Currently DISABLED in the
    opencode config: upstream v0.1.1 crashes (mcp 2.x removed
    `mcp.server.fastmcp`; mcp 1.9.0 still fails tool registration). Do NOT
    enable until upstream is fixed; use appium-mcp / scrcpy-mcp / agent-device.

## Prerequisites (verify before use)

-   Target device/emulator visible via `adb devices` (ADB is at
    `/home/ubuntu/Android/Sdk/platform-tools`; ensure it is on PATH when
    invoking these servers).
-   Node.js 22+ is required by appium-mcp, scrcpy-mcp and agent-device — use
    `/opt/node22/bin/npx` (system node is v18 and too old).
-   scrcpy and ffmpeg are optional but recommended for scrcpy-mcp performance;
    the server falls back to ADB when they are absent.
-   uv/uvx is used for the Python-based uiautomator2-mcp (currently disabled).

## Usage Rules

-   When a task matches one of these servers, prefer the server's MCP tools
    over raw `adb shell` / `uiautomator dump` invocations.
-   Verify the server is connected (its tools are actually available) before
    relying on it; if a server fails to start, report the error and fall back
    to the next appropriate server rather than guessing.
-   Confirm the target device with the server's device-listing tool first
    (the usual target for this workspace is emulator `emulator-5554`).


# MCP Verification Enforcement

Before ANY implementation, the agent MUST use the Approved Official
Documentation MCP Sources listed above (context7, ref, gitmcp, deepwiki, exa,
etc.) to fetch and verify all documentation. Direct web/curl fetching is NOT a
substitute for MCP-based documentation retrieval. The agent MUST NOT begin any
coding change until documentation verification is completed via MCP sources.

Before ANY implementation:

1.  Identify technologies involved.
2.  Locate official documentation via the approved MCP sources.
3.  Verify versions via MCP-fetched official documentation.
4.  Verify APIs via MCP-fetched official documentation.
5.  Verify security recommendations via MCP-fetched official documentation.
6.  Verify compatibility via MCP-fetched official documentation.
7.  Verify migration notes and breaking changes via MCP-fetched official
    documentation.

Only after MCP-based verification may implementation begin.

------------------------------------------------------------------------

# Anti-Hallucination Rule

The agent MUST NEVER fabricate:

-   APIs
-   Commands
-   Versions
-   Libraries
-   Configuration
-   Features
-   Compatibility claims

If uncertain:

"I need official documentation verification before proceeding."

------------------------------------------------------------------------

# Universal Problem Decomposition

Every problem MUST be divided:

Mission → Phase → Milestone → Task → Atomic Change

Every atomic change must be:

-   Small
-   Necessary
-   Testable
-   Reversible
-   Documented
-   Secure

------------------------------------------------------------------------

# Mandatory Engineering Workflow

## Phase 1: Understand

Identify:

-   Objective
-   Current behavior
-   Expected behavior
-   Constraints
-   Acceptance criteria
-   Risks

## Phase 2: Inspect

Inspect:

-   Repository structure
-   Source code
-   Configuration
-   Dependencies
-   Build system
-   Runtime environment
-   CI/CD
-   Tests
-   Documentation

Never modify unfamiliar code.

## Phase 3: Version Discovery

Verify:

-   Language versions
-   Framework versions
-   SDK versions
-   Libraries
-   Compilers
-   Platforms
-   Toolchains

## Phase 4: Documentation Verification

Verify — using ONLY the Approved Official Documentation MCP Sources (context7,
ref, gitmcp, deepwiki, exa, etc.) — the following for every technology
involved. Direct web/curl fetching is NOT a substitute for MCP-based
documentation retrieval:

1.  Official documentation
2.  Official specifications
3.  Official API references
4.  Official SDK documentation
5.  Official repositories
6.  Release notes
7.  Migration guides

------------------------------------------------------------------------

# Verification Report Before Changes

Before editing:

## Technology Inventory

Technology: Version: Official Source: Verification Result:

## Documentation Evidence

Source: Reference: Finding: Compatibility: Security Notes:

## Implementation Justification

Explain:

-   Why solution is correct
-   Why alternatives were rejected
-   Security reasoning
-   Compatibility reasoning

## Impact Analysis

Analyze:

-   Existing behavior
-   New behavior
-   Risks
-   Security
-   Performance
-   Compatibility
-   Rollback strategy
-   Testing strategy

------------------------------------------------------------------------

# Safe Implementation Rules

Every change MUST:

-   Follow existing architecture
-   Minimize changes
-   Preserve compatibility
-   Use secure defaults
-   Include validation

------------------------------------------------------------------------

# Dependency Security

Before adding dependencies verify:

-   Official package source
-   Authenticity
-   Security advisories
-   License
-   Maintenance status
-   Compatibility

Never install unknown packages.

------------------------------------------------------------------------

# Secret Protection

Always:

-   Protect credentials
-   Use secret managers
-   Apply least privilege
-   Validate permissions

Never:

-   Hardcode secrets
-   Commit tokens
-   Disable security controls

------------------------------------------------------------------------

# Testing Requirements

Before completion:

Verify:

-   Build success
-   Unit tests
-   Integration tests
-   UI tests
-   Static analysis
-   Lint checks
-   Security checks
-   Regression safety

------------------------------------------------------------------------

# Atomic Execution Loop

1.  Discover
2.  Verify official documentation via the Approved MCP Sources
3.  Plan
4.  Implement
5.  Test
6.  Review
7.  Document
8.  Commit
9.  Push
10. Monitor

------------------------------------------------------------------------

# Git Discipline

Every atomic change requires:

-   Meaningful commit message
-   Explanation of change
-   Reason for change
-   Validation performed

Example:

fix(auth): handle token refresh failure after official documentation
verification

------------------------------------------------------------------------

# Production Readiness Standard

Every delivered change must be:

Correct\
Secure\
Reliable\
Maintainable\
Compatible\
Tested\
Documented\
Auditable\
Reversible\
Production Ready

------------------------------------------------------------------------

# Project-Critical GitHub Repositories (MANDATORY MCP Verification)

## Scope

The following GitHub repositories are the CORE engines of this project
("NGO Report Studio"). The agent MUST consult them via MCP servers every time
work touches the technology they own — before ANY code change, bug fix,
debugging, dependency change, API usage, configuration change, or migration
involving them. This is ABSOLUTE / MANDATORY / NON-NEGOTIABLE / ZERO
EXCEPTIONS.

Direct web/curl fetching is NOT a substitute. The agent MUST use the Approved
Official Documentation MCP Sources (deepwiki, context7, ref, gitmcp) to fetch
the official repository documentation, verify versions, verify APIs, verify
security recommendations, verify compatibility, and verify migration notes
BEFORE implementation begins.

## The Repositories (in order of importance)

1.  **python-openxml/docxtpl** — THE single most important repository.
    DOCX templates with `{{ placeholder }}` fields (built in Word), filled
    with the customer's data at runtime → outputs a fully editable `.docx`.
    This IS the "generate from template" engine (industry standard:
    jinja2 + python-docx).

    MUST verify via MCP before use: `DocxTemplate`, `.render(context)`,
    `.save()`, `InlineImage`, `Mm/Inches/Pt` units, jinja2 syntax and
    escaping behavior, image insertion, and any version changes.

2.  **python-openxml/python-docx** — programmatic DOCX creation/editing
    (add tables, replace placeholder images) — works alongside docxtpl.

    MUST verify via MCP before use: `Document`, `Paragraph`, `Run`,
    `Run.add_picture`, `Run.clear()`, `Paragraph.clear()`, table APIs,
    sections/headers/footers, and any version changes.

3.  **ueberdosis/tiptap** — browser-based rich-text editor (React) for the
    "edit your report" phase — customers edit text/images inline before
    downloading. (Alternative: CKEditor 5, free open-source.)

    MUST verify via MCP before use: `@tiptap/react` packages, `useEditor`,
    `EditorContent`, `StarterKit`, `immediatelyRender` (SSR), `onUpdate`,
    `getHTML()` / `getJSON()`, extension APIs, and any version changes.

4.  **jgm/pandoc** — converts the generated DOCX → PDF for download (the
    polish step). Works headless.

    MUST verify via MCP before use: the specific `pandoc` command
    invocation, filters, DOCX→PDF fidelity expectations, and any version
    changes.

5.  **LibreOffice headless** (`libreoffice --headless --convert-to pdf`) —
    battle-tested DOCX→PDF conversion with perfect fidelity (better than
    pandoc for complex layouts). Preferred for PDF export.

    MUST verify via MCP before use: the exact headless conversion
    invocation, output behavior, sandbox/worker constraints, and any
    version changes.

6.  **pydantic** — schema validation of the form inputs (or use
    great-expectations on top).

    MUST verify via MCP before use: model definition, validators, field
    types, JSON schema generation, version-specific behavior, and any
    breaking changes between major versions.

7.  **FastAPI (Python)** or **Next.js (Node)** — the web app framework
    tying form → docxtpl → editor → download.

    MUST verify via MCP before use: routing, dependencies, security
    (JWT/OAuth2), request validation, file uploads, static/exports,
    middleware, and any version changes.

## Mandatory MCP Workflow For These Repositories

Before ANY implementation involving any repository above, the agent MUST:

1.  Identify which repository/technology the task touches.
2.  Use the Approved Official Documentation MCP Sources in this priority
    order:
    -   **deepwiki** — `read_wiki_structure`, then `read_wiki_contents` /
        `ask_question` for the repository (owner/repo form, e.g.
        `python-openxml/docxtpl`).
    -   **context7** — `resolve-library-id` then `query-docs` for the
        official library documentation (e.g. docxtpl, python-docx, TipTap,
        FastAPI, pydantic).
    -   **ref** — `ref_search_documentation` / `ref_read_url` as a
        supplementary source.
    -   **gitmcp** — for repository/API/MCP-specific reference docs when
        applicable.
3.  Verify, via MCP-fetched official documentation: versions, APIs, security
    recommendations, compatibility, migration notes, and breaking changes.
4.  Record the verification (repository, MCP source, finding) before editing.
5.  Only after MCP-based verification passes may implementation begin.

## Safety And Success Rules (100% Perfect / 100% Successful / 100% Safe)

-   NEVER guess, assume, or implement from memory for any of these
    repositories — always verify via MCP first.
-   Verify the MCP server is actually connected and its tools are available
    BEFORE relying on it. If a server fails or lacks the content, report the
    error and fall back to the next Approved MCP source. NEVER fall back to
    guessing.
-   NEVER fabricate repository APIs, commands, versions, or compatibility
    claims. If uncertain: "I need official documentation verification before
    proceeding."
-   Do NOT make unnecessary changes to code. Every change must be small,
    necessary, testable, reversible, documented and secure, and must NOT
    break any existing functionality.
-   After any change to these engines, run the project's build, lint and
    test commands, and confirm regression safety before completion.

------------------------------------------------------------------------

# FINAL COMMANDMENT

NO IMPLEMENTATION WITHOUT OFFICIAL DOCUMENTATION VERIFICATION.

NO ASSUMPTION WITHOUT EVIDENCE.

NO MODIFICATION WITHOUT UNDERSTANDING.

NO COMPLETION WITHOUT VALIDATION.
