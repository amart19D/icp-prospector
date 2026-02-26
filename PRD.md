# ICP Prospector — Product Requirements Document

## Overview
A CLI tool that automates nightly discovery of high-fit prospects matching a user-defined Ideal Customer Profile (ICP). It searches public sources (X/Twitter, Reddit, Indie Hackers, Product Hunt, Hacker News), scores each lead, deduplicates, and outputs to Google Sheets and/or CSV.

**Initial use case:** Find bootstrapped SaaS founders publicly expressing support/docs pain, for outbound outreach.

---

## Goals
- Run unattended on a schedule (cron / systemd timer)
- User defines ICP + pain signals in a YAML config — no code changes required
- Score each lead (0–100) based on configurable fit criteria
- Deduplicate across runs by domain
- Output: append new leads to Google Sheets + write CSV backup
- Optional: post daily summary (Discord webhook or stdout)

---

## Non-goals (v1)
- No email finding / enrichment (Apollo/Clearbit)
- No outreach automation
- No UI / web dashboard
- No paid data sources

---

## Architecture

```
config/icp.yaml          ← user defines ICP, sources, scoring weights
prospector/
  cli.py                 ← main entry point (argparse)
  config.py              ← load + validate YAML config
  sources/
    base.py              ← abstract Source class
    x_search.py          ← X/Twitter via x_search_smart.py wrapper
    reddit.py            ← Reddit via web search (no API key needed)
    indie_hackers.py     ← Indie Hackers via web search
    product_hunt.py      ← Product Hunt via web search / feed
    hacker_news.py       ← HN via Algolia API (free, no key)
  enricher.py            ← fetch domain, detect stack, infer fit signals
  scorer.py              ← rules-based scoring engine
  deduplicator.py        ← domain-level dedup with persistent state
  outputs/
    sheets.py            ← Google Sheets append via gog CLI
    csv_writer.py        ← CSV output
    summary.py           ← daily summary formatter
  state.py               ← read/write seen_domains.json
run.py                   ← orchestrator: sources → enrich → score → dedup → output
```

---

## Config Schema (config/icp.yaml)

```yaml
icp:
  name: "Bootstrapped SaaS Support Pain"
  
  # Keywords to search across all sources
  pain_keywords:
    - "support is killing me"
    - "same questions over and over"
    - "help docs are a mess"
    - "intercom too expensive"
    - "drowning in support tickets"
    - "hire support person"
    - "customers keep asking"
    - "Crisp alternative"
    - "HelpScout alternative"

  # Keywords that DISQUALIFY a lead
  exclude_keywords:
    - "enterprise"
    - "B2C"
    - "hiring manager"

  # Scoring weights (0–1, must sum ≤ 1 each)
  scoring:
    pain_signal_present: 30      # explicit pain quote found
    b2b_saas_signals: 25         # pricing page, "dashboard", "API", "integrations"
    small_team_signals: 20       # "indie", "solo founder", "bootstrapped", "just me"
    helpdesk_stack_detected: 15  # Intercom/HelpScout/Crisp/Zendesk found on site
    docs_present: 10             # has /docs or /help subdomain

sources:
  x: true
  reddit:
    subreddits: [SaaS, microsaas, startups, indiehackers]
  indie_hackers: true
  product_hunt: true
  hacker_news: true

output:
  google_sheets:
    enabled: true
    sheet_id: ""           # fill in after sheet is created
    tab_name: "Prospects"
  csv:
    enabled: true
    path: "output/leads.csv"
  summary:
    enabled: true
    mode: stdout           # stdout | discord
    discord_webhook: ""

state:
  seen_domains_file: "state/seen_domains.json"
```

---

## Google Sheets Schema (columns)

| Column | Description |
|--------|-------------|
| Date Found | ISO date |
| Company/Product | Inferred name |
| Website | Domain |
| Source | x / reddit / ih / ph / hn |
| Evidence URL | Link to original post |
| Pain Quote | Snippet from post |
| Support Stack | Intercom / HelpScout / Crisp / none / unknown |
| Docs URL | /docs or /help if found |
| Fit Score | 0–100 |
| Status | New / Reviewing / Contacted / Disqualified |
| Notes | Empty (for human use) |

---

## Lead Data Model (internal)

```python
@dataclass
class Lead:
    domain: str
    company: str
    source: str           # x|reddit|ih|ph|hn
    evidence_url: str
    pain_quote: str
    support_stack: str    # detected stack or "unknown"
    docs_url: str
    fit_score: int        # 0–100
    date_found: str       # ISO
    status: str = "New"
    notes: str = ""
```

---

## Scoring Logic (scorer.py)

```
score = 0
if pain_quote present and non-empty:         score += 30
if b2b_saas_signals in page content:        score += 25  (partial: 10–25 based on count)
if small_team_signals detected:             score += 20
if support_stack detected on domain:        score += 15
if docs_url found:                          score += 10
```

Thresholds:
- 70–100 = High fit → include, highlight in summary
- 40–69  = Medium fit → include
- 0–39   = Low fit → discard (don't write to sheet)

---

## Deduplication

- Maintain `state/seen_domains.json` — dict of `{domain: first_seen_date}`
- Before writing any lead, check domain against seen set
- If domain seen + score improved significantly (>15 pts): update existing row, don't append new
- If domain seen + score similar: skip

---

## Source Implementation Notes

### X/Twitter
- Wrap existing `scripts/x_search_smart.py` (already available on VPS at `/root/.openclaw/workspace/skills/x-search/scripts/x_search_smart.py`)
- Query each pain_keyword, max 10 results per query, dedupe by URL
- Extract: tweet text (pain_quote), user profile URL → extract domain if linked

### Reddit
- Use Pushshift/Reddit JSON API: `https://www.reddit.com/r/{sub}/search.json?q={keyword}&sort=new&limit=25`
- No API key required
- Extract: post title + snippet, link to post, any domain mentioned in post text

### Indie Hackers
- Web search: `site:indiehackers.com {keyword}` via Brave/DuckDuckGo
- Fetch page → extract post snippet

### Product Hunt
- Use existing `hn-ph.sh` fallback chain or direct feed parse
- Focus on newly launched SaaS products (not pain-keyword search — these are cold outreach targets)
- Score lower by default (no pain signal) but flag as "cold outreach opportunity"

### Hacker News
- Algolia API: `https://hn.algolia.com/api/v1/search?query={keyword}&tags=story,comment&hitsPerPage=20`
- Free, no auth
- Extract: objectID, url, text snippet

---

## Enricher (enricher.py)

For each lead with a domain:
1. `requests.get(domain, timeout=5)` — get homepage HTML
2. Detect support stack: search for `intercom`, `helpscout`, `crisp`, `zendesk`, `freshdesk`, `gorgias` in HTML source
3. Detect docs: check if `/docs`, `/help`, `/support`, `/kb` returns 200
4. Detect B2B SaaS signals: look for "dashboard", "API", "integrations", "pricing", "team" in page text
5. Detect small team: look for "indie", "bootstrapped", "solo", "founder", "small team" in About page

---

## CLI Interface

```bash
# Run full pipeline
python -m prospector run

# Run specific source only
python -m prospector run --source reddit

# Dry run (no sheet writes, print results)
python -m prospector run --dry-run

# Show current lead count + score distribution
python -m prospector stats

# Clear seen_domains (reset dedup state)
python -m prospector reset-state
```

---

## Setup / Installation

```bash
git clone https://github.com/amart19D/icp-prospector.git
cd icp-prospector
pip install -r requirements.txt
cp config/icp.example.yaml config/icp.yaml
# edit config/icp.yaml with your ICP + sheet ID
python -m prospector run --dry-run
```

Dependencies: `requests`, `pyyaml`, `rich` (terminal output), `python-dotenv`
Optional: `gog` CLI (for Google Sheets output)

---

## File Structure (target)

```
icp-prospector/
├── README.md
├── PRD.md
├── requirements.txt
├── setup.py (or pyproject.toml)
├── config/
│   ├── icp.example.yaml
│   └── icp.yaml             ← gitignored (personal config)
├── prospector/
│   ├── __init__.py
│   ├── cli.py
│   ├── config.py
│   ├── run.py
│   ├── enricher.py
│   ├── scorer.py
│   ├── deduplicator.py
│   ├── state.py
│   ├── sources/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── x_search.py
│   │   ├── reddit.py
│   │   ├── indie_hackers.py
│   │   ├── product_hunt.py
│   │   └── hacker_news.py
│   └── outputs/
│       ├── __init__.py
│       ├── sheets.py
│       ├── csv_writer.py
│       └── summary.py
├── state/
│   └── .gitkeep
├── output/
│   └── .gitkeep
└── .gitignore
```

---

## Success Criteria (v1)

- [ ] `prospector run` completes without error on all 5 sources
- [ ] Leads with fit_score >= 40 appear in Google Sheet with all columns populated
- [ ] Re-running does not duplicate leads (dedup works)
- [ ] Config change (new keyword) takes effect on next run without code change
- [ ] Nightly cron run produces ≥5 new leads per night on average
- [ ] README is clear enough for a non-technical founder to set up in 15 min
