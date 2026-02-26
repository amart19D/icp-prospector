from __future__ import annotations

import csv
from pathlib import Path

from prospector.models import Lead

HEADERS = [
    "Date Found",
    "Company/Product",
    "Website",
    "Source",
    "Evidence URL",
    "Pain Quote",
    "Support Stack",
    "Docs URL",
    "Fit Score",
    "Status",
    "Notes",
]


def write_leads_csv(path: str, leads: list[Lead]) -> None:
    csv_path = Path(path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not csv_path.exists()

    with csv_path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        if write_header:
            writer.writerow(HEADERS)
        for lead in leads:
            writer.writerow(lead.to_row())


def read_leads_csv(path: str) -> list[dict[str, str]]:
    csv_path = Path(path)
    if not csv_path.exists():
        return []
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader)
