from __future__ import annotations

import logging
from datetime import datetime, timezone

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from prospector.config import load_config
from prospector.deduplicator import Deduplicator
from prospector.enricher import Enricher
from prospector.http import RequestManager
from prospector.models import Lead
from prospector.outputs.csv_writer import write_leads_csv
from prospector.outputs.report import generate_markdown_report
from prospector.outputs.sheets import append_to_sheets
from prospector.outputs.summary import emit_summary, summarize_discard_reasons
from prospector.scorer import Scorer
from prospector.sources import HackerNewsSource, IndieHackersSource, ProductHuntSource, RedditSource, XSearchSource
from prospector.state import load_seen_domains, save_seen_domains

logger = logging.getLogger("prospector.run")


def _expand_keywords(config: dict) -> tuple[list[str], dict[str, set[str]]]:
    seeds = [kw.strip() for kw in config["icp"]["pain_keywords"] if kw.strip()]
    expansions = config["icp"].get("keyword_expansions", {})
    all_keywords: list[str] = []
    reverse_map: dict[str, set[str]] = {}

    for seed in seeds:
        low_seed = seed.lower()
        all_keywords.append(seed)
        reverse_map.setdefault(low_seed, set()).add(low_seed)
        for variant in expansions.get(seed, []):
            if variant and variant not in all_keywords:
                all_keywords.append(variant)
            reverse_map.setdefault(variant.lower(), set()).add(low_seed)

    return all_keywords, reverse_map


def _source_rpm(config: dict, source_name: str, default_value: int) -> int:
    source_cfg = config["sources"].get(source_name)
    if isinstance(source_cfg, dict):
        return int(source_cfg.get("requests_per_minute", default_value))
    return int(config["sources"].get(f"{source_name}_requests_per_minute", default_value))


def build_sources(config: dict, request_manager: RequestManager, throttle_multiplier: float) -> list:
    sources = []
    source_cfg = config["sources"]

    if source_cfg.get("reddit"):
        sources.append(
            RedditSource(
                request_manager,
                requests_per_minute=_source_rpm(config, "reddit", 30),
                throttle_multiplier=throttle_multiplier,
            )
        )
    if source_cfg.get("hacker_news", False):
        sources.append(
            HackerNewsSource(
                request_manager,
                requests_per_minute=_source_rpm(config, "hacker_news", 40),
                throttle_multiplier=throttle_multiplier,
            )
        )
    if source_cfg.get("x", False):
        sources.append(
            XSearchSource(
                request_manager,
                requests_per_minute=_source_rpm(config, "x", 20),
                throttle_multiplier=throttle_multiplier,
            )
        )
    if source_cfg.get("indie_hackers", False):
        sources.append(
            IndieHackersSource(
                request_manager,
                requests_per_minute=_source_rpm(config, "indie_hackers", 20),
                throttle_multiplier=throttle_multiplier,
            )
        )
    if source_cfg.get("product_hunt", False):
        sources.append(
            ProductHuntSource(
                request_manager,
                requests_per_minute=_source_rpm(config, "product_hunt", 20),
                throttle_multiplier=throttle_multiplier,
            )
        )

    return sources


def run_pipeline(
    config_path: str = "config/icp.yaml",
    selected_source: str | None = None,
    dry_run: bool = False,
    throttle: bool = False,
) -> dict:
    config = load_config(config_path)
    request_manager = RequestManager(timeout_seconds=int(config.get("http", {}).get("timeout_seconds", 10)))
    throttle_multiplier = 2.0 if throttle else 1.0
    sources = build_sources(config, request_manager, throttle_multiplier)

    if selected_source:
        selected_source = selected_source.lower()
        sources = [source for source in sources if source.name == selected_source or source.name.replace("_", "-") == selected_source]

    if not sources:
        raise ValueError("No sources enabled or matching source selection")

    all_keywords, reverse_keyword_map = _expand_keywords(config)
    scorer = Scorer(config["icp"]["scoring"])
    enricher = Enricher(request_manager)
    seen = load_seen_domains(config["state"]["seen_domains_file"])
    deduper = Deduplicator(seen)

    started_at = datetime.now(timezone.utc)
    source_counts: dict[str, int] = {}
    raw_leads: list[Lead] = []

    console = Console()
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
        source_task = progress.add_task("Fetching sources", total=len(sources))
        for source in sources:
            leads = source.safe_fetch(all_keywords, config)
            for lead in leads:
                for hit in list(lead.keyword_hits):
                    lead.keyword_variant_hits.update(reverse_keyword_map.get(hit.lower(), set()))
            raw_leads.extend(leads)
            source_counts[source.name] = len(leads)
            progress.advance(source_task)

        enrich_task = progress.add_task("Enriching and scoring leads", total=len(raw_leads) or 1)
        for lead in raw_leads:
            lead_text = f"{lead.pain_quote} {lead.company}".lower()
            if any(ex.lower() in lead_text for ex in config["icp"]["exclude_keywords"]):
                lead.discard_reason = "excluded_keyword"
                progress.advance(enrich_task)
                continue
            enricher.enrich(lead)
            scorer.score(lead)
            progress.advance(enrich_task)

    scored = [lead for lead in raw_leads if lead.fit_score >= 40 and not lead.discard_reason]
    low_fit = [lead for lead in raw_leads if lead.fit_score < 40 and not lead.discard_reason]
    for lead in low_fit:
        lead.discard_reason = "low_score"

    new_leads, seen_skipped = deduper.split_new_and_seen(scored)
    today = datetime.now(timezone.utc).date().isoformat()
    deduper.mark(new_leads, today)

    if not dry_run:
        if config["output"]["csv"].get("enabled", True):
            write_leads_csv(config["output"]["csv"]["path"], new_leads)

        sheets_cfg = config["output"]["google_sheets"]
        if sheets_cfg.get("enabled", False):
            try:
                append_to_sheets(
                    sheet_id=sheets_cfg.get("sheet_id", ""),
                    tab_name=sheets_cfg.get("tab_name", "Prospects"),
                    leads=new_leads,
                    account=sheets_cfg.get("account") or None,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Google Sheets append failed: %s", exc)

        save_seen_domains(config["state"]["seen_domains_file"], deduper.seen_domains)

    discarded = [lead for lead in raw_leads if lead.discard_reason] + seen_skipped
    discarded_reasons = summarize_discard_reasons(discarded)

    ended_at = datetime.now(timezone.utc)
    generate_markdown_report(
        output_path="output/last-run-report.md",
        started_at=started_at,
        ended_at=ended_at,
        source_counts=source_counts,
        kept_leads=new_leads,
        discarded_reasons=discarded_reasons,
    )

    summary_cfg = config["output"]["summary"]
    if summary_cfg.get("enabled", True):
        emit_summary(summary_cfg.get("mode", "stdout"), summary_cfg.get("discord_webhook", ""), new_leads, len(discarded))

    _print_run_table(console, source_counts, new_leads, discarded_reasons)

    return {
        "new_leads": new_leads,
        "discarded": discarded,
        "source_counts": source_counts,
    }


def _print_run_table(console: Console, source_counts: dict[str, int], leads: list[Lead], discarded_reasons: dict[str, int]) -> None:
    table = Table(title="ICP Prospector Run Summary")
    table.add_column("Metric")
    table.add_column("Value", justify="right")

    table.add_row("Sources", str(len(source_counts)))
    for src, count in sorted(source_counts.items()):
        table.add_row(f"  - {src}", str(count))

    high = sum(1 for lead in leads if lead.fit_score >= 70)
    medium = sum(1 for lead in leads if 40 <= lead.fit_score < 70)
    table.add_row("Kept Leads", str(len(leads)))
    table.add_row("High", str(high))
    table.add_row("Medium", str(medium))
    table.add_row("Discard Reasons", str(discarded_reasons))

    console.print(table)
