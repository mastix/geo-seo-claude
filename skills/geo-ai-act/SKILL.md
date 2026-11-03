---
name: geo-ai-act
description: EU AI Act Article 50 transparency pre-check for websites. Scans images for embedded AI provenance markers (C2PA / Content Credentials, IPTC DigitalSourceType, generator metadata), checks whether AI images that qualify as deep fakes carry a visible "AI-generated" label, and checks chatbots and AI-written public-interest text for disclosure. Use when user says "AI Act", "KI-Verordnung", "Artikel 50", "Article 50", "KI-Kennzeichnung", "AI label", "AI-generated images", "deepfake", "KI-Bilder kennzeichnen", or "chatbot disclosure". Not legal advice.
version: 1.0.0
author: geo-seo-claude
tags: [legal, ai-act, transparency, deepfake, c2pa, labelling, chatbot]
allowed-tools: Read, Grep, Glob, Bash, WebFetch, WebSearch, Write
---

# GEO AI Act Transparency Check (Art. 50)

## Purpose

Since 2 August 2026, Article 50 of the EU AI Act requires transparency for certain AI content. The duty that hits most websites is narrower than "label every AI image":

- **AI images, audio or video that are deep fakes** must be visibly disclosed. A deep fake looks like real people, things, places or events and could be taken for authentic.
- **Chatbots** must make clear that users are talking to an AI.
- **AI-written text on matters of public interest** must be disclosed, unless it was human-reviewed under editorial responsibility.

This skill checks those duties from the outside. It reads provenance metadata embedded in images, finds visible labels and judges the deep-fake question per AI image.

It runs in two contexts:

1. **Standalone:** `/geo ai-act <url>` → writes `GEO-AI-ACT-CHECK.md` to the current working directory.
2. **In `/geo audit`:** the `geo-ai-act` subagent runs in Phase 2b, next to `geo-legal`, and its section goes into `GEO-AUDIT-REPORT.md`.

## How to Use This Skill

1. Take the URL from the arguments. If none is given, ask for it.
2. Pick up to 10 image-heavy pages: homepage, about/team, news/blog/recipes, product/service pages, galleries. Use the sitemap or homepage navigation.
3. Delegate to the **`geo-ai-act` subagent** (`agents/geo-ai-act.md`, installed to `~/.claude/agents/geo-ai-act.md`) with the URL, the page list and the business type. If subagents are unavailable, follow that file yourself. It is the single source of truth for the rules, the steps and the severity mapping.
4. The procedure, in short:
   - **Step 1:** verify the current Article 50 rules and dates against primary sources (mandatory).
   - **Steps 2–3:** determine the site's role, then scan with
     `python3 ~/.claude/skills/geo/scripts/ai_content_scanner.py <urls...> --max-images 15`
   - **Step 4:** deep-fake test per AI image (look at it), and label quality.
   - **Step 5:** chatbot disclosure and AI text.
   - **Step 6:** overall status and severities.
5. Write `GEO-AI-ACT-CHECK.md` with a title block (site, date, URL, business type) followed by the agent's section. Print a short terminal summary: status, AI images found / labelled / unlabelled, High findings.

## Rules

- Never claim an image is AI-generated without a marker, a label or the operator's own statement. "No signal" means "unknown".
- Read-only. Respect the quality gates (≥ 1 s between requests, 30 s timeout).
- Always include the not-legal-advice disclaimer. There is no numeric score; the status is reported separately from the GEO Score.

## Output

| File | Contents |
|---|---|
| `GEO-AI-ACT-CHECK.md` | Disclaimer, status, what Art. 50 requires for this site, legal baseline table, AI image table with deep-fake verdicts, chatbot and AI text assessment, Needs Review, findings by severity, recommended actions |
