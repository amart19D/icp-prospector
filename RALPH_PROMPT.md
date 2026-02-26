# ICP Prospector — Ralph Loop Build Prompt

## Project
Build `icp-prospector`: a Python CLI tool that finds high-fit leads matching a user-defined Ideal Customer Profile (ICP) by searching public sources (X/Twitter, Reddit, Indie Hackers, Product Hunt, Hacker News), scoring each lead, deduplicating, and outputting to Google Sheets and CSV.

Full spec: `PRD.md` in this repo. Read it completely before writing any code.

## Your job
Implement the full project as described in PRD.md. Work iteratively — get each layer working before moving to the next:

1. **Foundation first:** project structure, `__init__.py` files, `config.py` (YAML loader + validation), `Lead` dataclass, `state.py` (seen_domains.json read/write)
2. **Sources:** implement each source class (reddit first — easiest, no auth), then HN (Algolia API), then X wrapper, then IH + PH (web search fallback)
3. **Enricher:** domain fetch, stack detection, docs detection, B2B/small-team signals
4. **Scorer:** rules-based scoring per PRD spec
5. **Deduplicator:** domain-level dedup using state file
6. **Outputs:** CSV writer first, then Google Sheets via `gog` CLI wrapper
7. **CLI:** `prospector run`, `prospector stats`, `prospector reset-state` via argparse
8. **Orchestrator:** `run.py` wires all pieces together
9. **Config example + README**

## Rules
- Write working, runnable code — no stubs, no TODOs unless truly blocked
- Prefer simple/explicit over clever — this will be read by non-experts
- Use `rich` for terminal output (progress, tables, colored summary)
- Every source must gracefully handle failures (timeout, 429, empty result) — log warning and continue, never crash the whole run
- Respect rate limits: add small sleeps between requests per source
- No hardcoded credentials — everything via config/env
- `.gitignore` must exclude: `config/icp.yaml`, `state/`, `output/`, `.env`, `__pycache__`
- When complete, write the file `RALPH_DONE` with a one-line summary of what was built

## Environment context
- Python 3.11+ on Ubuntu 24.04 (arm64)
- `gog` CLI is available at `/usr/bin/gog` (Google Workspace CLI for Sheets)
- X search script available at: `/root/.openclaw/workspace/skills/x-search/scripts/x_search_smart.py`
  - Call it as: `python3 /root/.openclaw/workspace/skills/x-search/scripts/x_search_smart.py --query "..." --max 20 --no-retweets`
  - Returns JSON to stdout
- All installs go via `pip install` (no brew, no sudo needed)
- Working directory: `/root/.openclaw/workspace/icp-prospector`

## Google Sheets output note
The `gog` CLI command to append rows:
```bash
gog sheets append <SHEET_ID> "Prospects!A:K" \
  --values-json '[["2026-01-01","Acme","acme.com","reddit","https://...","pain quote","Intercom","https://acme.com/docs",72,"New",""]]' \
  --insert INSERT_ROWS \
  --account ronan.assistant@gmail.com
```
The `outputs/sheets.py` should build this command and call it via `subprocess`.

## Extended scope (do all of this)

After the core pipeline works, also build:

### 10. Test suite (`tests/`)
Write `pytest` tests for:
- `config.py` — loads valid YAML, raises on missing required fields
- `scorer.py` — correct score for known inputs (unit tests, no network)
- `deduplicator.py` — correctly blocks seen domains, allows new ones
- `enricher.py` — mock `requests.get`, assert stack detection works
- `sources/reddit.py` — mock HTTP response, assert Lead extraction

### 11. GitHub Actions CI (`.github/workflows/ci.yml`)
- Trigger: push + PR to main
- Steps: checkout, python 3.11 setup, pip install, pytest
- Badge: add CI status badge to README

### 12. Rich HTML/Markdown run report (`outputs/report.py`)
After each run, generate `output/last-run-report.md` with:
- Run timestamp + duration
- Sources searched + lead count per source
- Score distribution (histogram in text: High/Medium/Low counts)
- Top 5 leads table (company, score, pain quote snippet, source)
- Discard count + reasons summary

### 13. `--export` flag
`python -m prospector export --format markdown` — dumps all leads from CSV as a formatted markdown table, sorted by fit score descending. Good for pasting into Notion or a brief.

### 14. Retry + rate limit handling
- Exponential backoff decorator for all HTTP requests (max 3 retries, 2/4/8s delays)
- Per-source configurable `requests_per_minute` in config YAML
- Global `--throttle` flag to slow all sources by 2x (for polite scraping)

### 15. Keyword expansion (config)
Support `icp.keyword_expansions` in config — a dict that maps a seed keyword to related variants auto-appended to search queries. Example:
```yaml
keyword_expansions:
  "support is killing me":
    - "support tickets overwhelming"
    - "drowning in support"
```
Scorer gives +5 bonus if multiple keyword variants hit on same lead.

### 16. Prospect detail page scraper
For each lead domain, also attempt to scrape `/about` and `/team` pages. Extract:
- Team size signals ("just the two of us", "small team of 3")
- Founder name if mentioned
- Location (optional)
Store in Lead dataclass as `team_size_signal: str` and `founder_name: str`.

## Done signal
When ALL of the following are true:
- `python -m prospector run --dry-run` completes without error
- At least reddit + HN sources return results
- Scoring produces leads with scores in expected range
- CSV output writes correctly
- README.md is complete

Write the file `RALPH_DONE` with contents: `"ICP Prospector v1 complete — <brief summary of what works>"`
