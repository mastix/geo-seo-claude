---
name: geo-legal
description: Legal compliance pre-check for websites and online shops (DE/AT/CH + EU focus). Verifies the current legal baseline against primary sources, then checks the imprint (Impressum), the privacy policy (Datenschutzerklärung) against the technologies the site actually loads, consent behaviour before opt-in, and the terms and conditions (AGB) if present. Use when user says "legal", "Impressum", "imprint", "Datenschutz", "Datenschutzerklärung", "privacy policy", "AGB", "terms", "DSGVO", "GDPR", "cookie consent", "Rechtstexte", or "Abmahnung". Produces a Legal Compliance Score (0-100) that is reported separately from the GEO Score. Not legal advice.
version: 1.0.0
author: geo-seo-claude
tags: [legal, impressum, privacy, gdpr, dsgvo, tdddg, agb, consent, compliance]
allowed-tools: Read, Grep, Glob, Bash, WebFetch, WebSearch, Write
---

# GEO Legal Compliance Check

## Purpose

AI search engines and customers both reward trustworthy sites. Legal pages are also a common source of liability in the DACH region: warning letters (Abmahnungen) for incomplete imprints, privacy policies that do not match the trackers actually used, and tracking before consent. This skill checks the three core legal texts against **current** law and against what the site really loads.

It runs in two contexts:

1. **Standalone:** `/geo legal <url>` → writes `GEO-LEGAL-COMPLIANCE.md` to the current working directory.
2. **As the last step of `/geo audit`:** the orchestrator launches the `geo-legal` subagent after the five parallel subagents finish and passes their technology findings in. The result becomes the "Legal Compliance" section of `GEO-AUDIT-REPORT.md`.

## How to Use This Skill

1. Take the URL from the arguments. If none is given, ask for it.
2. Detect the business type from the homepage (same rules as `geo/SKILL.md` → Business Type Detection). It decides which consumer-law checks apply.
3. Delegate to the **`geo-legal` subagent** (`agents/geo-legal.md`, installed to `~/.claude/agents/geo-legal.md`) with the URL, business type and an output path for its section. If subagents are unavailable, follow the procedure in that agent file yourself, step by step. It is the single source of truth for the checks, the legal baseline and the scoring.
4. The procedure, in short:
   - **Step 1:** verify the legal baseline against primary sources (mandatory; laws change).
   - **Steps 2–3:** find the legal pages and build a technology inventory with
     `python3 ~/.claude/skills/geo/scripts/tech_detector.py <url> --browser`.
     Browser mode loads the page without consenting and records the requests and cookies that fire before consent.
   - **Steps 4–7:** check the Impressum, the Datenschutzerklärung (Art. 13 GDPR, technology coverage matrix, § 25 TDDDG consent), the AGB if present, and other mandatory e-commerce information.
   - **Step 8:** calculate the Legal Compliance Score and map findings to Critical/High/Medium/Low.
5. Write `GEO-LEGAL-COMPLIANCE.md` with the agent's section, preceded by a title block:

```markdown
# Legal Compliance Check: [Site Name]

**Date:** [Date]
**URL:** [URL]
**Business Type:** [Type]
**Jurisdiction assumed:** [e.g. DE + EU]
```

6. Print a short terminal summary: score, rating, Critical/High findings, and the "Needs Legal Review" items.

## Rules

- Read-only: never place orders, submit forms, create accounts or accept cookie banners.
- Always include the not-legal-advice disclaimer at the top of the output.
- The Legal Compliance Score is **not** part of the composite GEO Score.
- Respect the quality gates: ≤ 1 request/second, 30 s timeout per fetch, robots.txt respected unless the site owner authorised otherwise.

## Output

| File | Contents |
|---|---|
| `GEO-LEGAL-COMPLIANCE.md` | Disclaimer, Legal Compliance Score and breakdown, legal baseline verification table, technology inventory, Impressum / Datenschutz / AGB findings with verbatim quotes and suggested fixes, "Needs Legal Review" list, findings by severity, priority actions |
