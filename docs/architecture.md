# Architecture & Design

The repository is structured to seamlessly provide GEO+SEO support by using Claude's tool capabilities alongside agents and python utility scripts.

```
geo-seo-claude/
├── geo/                          # Main skill orchestrator
│   └── SKILL.md                  # Primary skill file with commands & routing
├── skills/                       # 17 specialized sub-skills
│   ├── geo-audit/                # Full audit orchestration & scoring
│   ├── geo-citability/           # AI citation readiness scoring
│   ├── geo-crawlers/             # AI crawler access analysis
│   ├── geo-llmstxt/              # llms.txt standard analysis & generation
│   ├── geo-brand-mentions/       # Brand presence on AI-cited platforms
│   ├── geo-platform-optimizer/   # Platform-specific AI search optimization
│   ├── geo-schema/               # Structured data for AI discoverability
│   ├── geo-technical/            # Technical SEO foundations
│   ├── geo-content/              # Content quality & E-E-A-T
│   ├── geo-report/               # Client-ready markdown report generation
│   ├── geo-report-pdf/           # Professional PDF report with charts
│   ├── geo-prospect/             # CRM-lite prospect pipeline management
│   ├── geo-proposal/             # Auto-generate client proposals
│   ├── geo-compare/              # Monthly delta tracking & progress reports
│   ├── geo-legal/                # Legal pre-check: Impressum, privacy policy, AGB
│   ├── geo-ai-act/               # EU AI Act Art. 50: AI image & chatbot labels
│   └── geo-update/               # Pull latest updates from upstream
├── agents/                       # 5 parallel subagents + 2 final checks
│   ├── geo-ai-visibility.md      # GEO audit, citability, crawlers, brands
│   ├── geo-platform-analysis.md  # Platform-specific optimization
│   ├── geo-technical.md          # Technical SEO analysis
│   ├── geo-content.md            # Content & E-E-A-T analysis
│   ├── geo-schema.md             # Schema markup analysis
│   ├── geo-legal.md              # Legal compliance (runs last)
│   └── geo-ai-act.md             # EU AI Act Art. 50 (runs last)
├── scripts/                      # Python utilities
│   ├── fetch_page.py             # Page fetching & parsing
│   ├── citability_scorer.py      # AI citability scoring engine
│   ├── brand_scanner.py          # Brand mention detection
│   ├── llmstxt_generator.py      # llms.txt validation & generation
│   ├── tech_detector.py          # Third-party tech & pre-consent detection
│   ├── ai_content_scanner.py     # AI image provenance & label detection
│   └── generate_pdf_report.py    # PDF report generator (ReportLab)
├── schema/                       # JSON-LD templates
│   ├── organization.json         # Organization schema (with sameAs)
│   ├── local-business.json       # LocalBusiness schema
│   ├── article-author.json       # Article + Person schema (E-E-A-T)
│   ├── software-saas.json        # SoftwareApplication schema
│   ├── product-ecommerce.json    # Product schema with offers
│   └── website-searchaction.json # WebSite + SearchAction schema
├── install.sh                    # One-command installer
├── uninstall.sh                  # Uninstaller
├── requirements.txt              # Python dependencies
└── README.md                     # Main project view
```

### Full Audit Flow

When you run `/geo audit https://example.com`:

1. **Discovery** — Fetches homepage, detects business type, crawls sitemap
2. **Parallel Analysis** — Launches 5 subagents simultaneously:
   - AI Visibility (citability, crawlers, llms.txt, brand mentions)
   - Platform Analysis (ChatGPT, Perplexity, Google AIO readiness)
   - Technical SEO (Core Web Vitals, SSR, security, mobile)
   - Content Quality (E-E-A-T, readability, freshness)
   - Schema Markup (detection, validation, generation)
3. **Legal Compliance** — After the parallel phase, `geo-legal` checks the Impressum, the privacy policy against the detected technologies, and the AGB, using current law (separate Legal Compliance Score), and `geo-ai-act` checks AI image and chatbot disclosure under EU AI Act Art. 50 (separate status)
4. **Synthesis** — Aggregates scores, generates composite GEO Score (0-100)
5. **Report** — Outputs prioritized action plan with quick wins

### Data Storage

The CRM and reporting skills (`/geo prospect`, `/geo proposal`, `/geo compare`) store runtime data outside the Claude Code directory:

```
~/.geo-prospects/
├── prospects.json              # Client/prospect pipeline data
├── proposals/                  # Generated proposal documents
│   └── <domain>-proposal-<date>.md
└── reports/                    # Monthly delta reports
    └── <domain>-monthly-<YYYY-MM>.md
```

This directory is **not removed** by the uninstaller — delete it manually if you no longer need your prospect data.
