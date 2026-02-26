# ICP Prospector

![CI](https://github.com/amart19D/icp-prospector/actions/workflows/ci.yml/badge.svg)

`icp-prospector` is a Python CLI that discovers ICP-matching leads from public sources (X, Reddit, Indie Hackers, Product Hunt, Hacker News), enriches/scores them, deduplicates by domain, and exports to CSV and Google Sheets.

## Features

- YAML-defined ICP and scoring rules
- Sources: Reddit, Hacker News (Algolia), X wrapper, Indie Hackers search fallback, Product Hunt launch scraping
- Enrichment: support stack detection, docs URL checks, B2B signals, `/about` + `/team` detail extraction
- Rules-based 0-100 fit scoring with keyword expansion bonus
- Domain deduplication persisted in `state/seen_domains.json`
- Outputs: CSV, Google Sheets append via `gog`, markdown run report
- CLI commands: `run`, `stats`, `reset-state`, `export`
- Retry/backoff and per-source request throttling

## Install

```bash
pip install -r requirements.txt
cp config/icp.example.yaml config/icp.yaml
# edit config/icp.yaml
```

## Usage

```bash
# full run
python -m prospector run

# run one source
python -m prospector run --source reddit

# dry run
python -m prospector run --dry-run

# polite slow mode (2x slower all sources)
python -m prospector run --throttle

# stats from CSV
python -m prospector stats

# clear dedup state
python -m prospector reset-state

# export CSV as markdown table
python -m prospector export --format markdown
```

## Config

Start from `config/icp.example.yaml`. Required sections:

- `icp`: keywords, excludes, scoring weights, optional `keyword_expansions`
- `sources`: enabled sources + `requests_per_minute`
- `output`: csv/sheets/summary settings
- `state`: path to seen domains file

## Google Sheets

If enabled, rows are appended via `gog`:

```bash
gog sheets append <SHEET_ID> "Prospects!A:K" --values-json '[...]' --insert INSERT_ROWS --account <ACCOUNT>
```

Set these in config:

- `output.google_sheets.enabled`
- `output.google_sheets.sheet_id`
- `output.google_sheets.tab_name`
- `output.google_sheets.account` (optional)

## Testing

```bash
pytest -q
```

## Output files

- `output/leads.csv`
- `output/last-run-report.md`
- `state/seen_domains.json`
