from __future__ import annotations

import argparse
import logging

from rich.console import Console
from rich.table import Table

from prospector.outputs.csv_writer import read_leads_csv
from prospector.run import run_pipeline
from prospector.state import load_seen_domains, reset_seen_domains


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="prospector", description="ICP Prospector CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    run_cmd = sub.add_parser("run", help="Run full prospecting pipeline")
    run_cmd.add_argument("--config", default="config/icp.yaml", help="Path to YAML config")
    run_cmd.add_argument("--source", default=None, help="Run only one source (reddit|hacker_news|x|indie_hackers|product_hunt)")
    run_cmd.add_argument("--dry-run", action="store_true", help="Run without writing sheets/csv/state")
    run_cmd.add_argument("--throttle", action="store_true", help="Slow all sources by 2x")

    stats_cmd = sub.add_parser("stats", help="Show CSV lead statistics")
    stats_cmd.add_argument("--config", default="config/icp.yaml", help="Path to YAML config")
    reset_cmd = sub.add_parser("reset-state", help="Clear seen domains state file")
    reset_cmd.add_argument("--config", default="config/icp.yaml", help="Path to YAML config")

    export_cmd = sub.add_parser("export", help="Export leads from CSV")
    export_cmd.add_argument("--format", choices=["markdown"], default="markdown")
    export_cmd.add_argument("--csv-path", default="output/leads.csv")

    return parser


def cmd_stats(config_path: str) -> int:
    from prospector.config import load_config

    cfg = load_config(config_path)
    csv_path = cfg["output"]["csv"].get("path", "output/leads.csv")
    rows = read_leads_csv(csv_path)

    high = sum(1 for row in rows if int(row.get("Fit Score", 0)) >= 70)
    medium = sum(1 for row in rows if 40 <= int(row.get("Fit Score", 0)) < 70)
    low = sum(1 for row in rows if int(row.get("Fit Score", 0)) < 40)

    table = Table(title="ICP Prospector Stats")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_row("CSV Path", csv_path)
    table.add_row("Total Leads", str(len(rows)))
    table.add_row("High", str(high))
    table.add_row("Medium", str(medium))
    table.add_row("Low", str(low))
    Console().print(table)
    return 0


def cmd_reset_state(config_path: str) -> int:
    from prospector.config import load_config

    cfg = load_config(config_path)
    state_path = cfg["state"]["seen_domains_file"]
    reset_seen_domains(state_path)
    Console().print(f"State reset: {state_path}")
    return 0


def cmd_export_markdown(csv_path: str) -> int:
    rows = read_leads_csv(csv_path)
    rows.sort(key=lambda row: int(row.get("Fit Score", 0)), reverse=True)

    lines = [
        "| Date Found | Company/Product | Website | Source | Evidence URL | Pain Quote | Fit Score |",
        "|---|---|---|---|---|---|---:|",
    ]
    for row in rows:
        lines.append(
            "| {date} | {company} | {website} | {source} | {url} | {quote} | {score} |".format(
                date=row.get("Date Found", "").replace("|", " "),
                company=row.get("Company/Product", "").replace("|", " "),
                website=row.get("Website", "").replace("|", " "),
                source=row.get("Source", "").replace("|", " "),
                url=row.get("Evidence URL", "").replace("|", " "),
                quote=(row.get("Pain Quote", "")[:140]).replace("|", " "),
                score=row.get("Fit Score", "0"),
            )
        )

    Console().print("\n".join(lines))
    return 0


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    parser = _build_parser()
    args = parser.parse_args()

    if args.command == "run":
        run_pipeline(config_path=args.config, selected_source=args.source, dry_run=args.dry_run, throttle=args.throttle)
        raise SystemExit(0)

    if args.command == "stats":
        raise SystemExit(cmd_stats(args.config))

    if args.command == "reset-state":
        raise SystemExit(cmd_reset_state(args.config))

    if args.command == "export":
        raise SystemExit(cmd_export_markdown(args.csv_path))

    raise SystemExit(1)
