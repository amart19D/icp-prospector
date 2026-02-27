from __future__ import annotations

import json
import subprocess

from prospector.models import Lead


def append_to_sheets(
    sheet_id: str,
    tab_name: str,
    leads: list[Lead],
    account: str | None = None,
    gog_bin: str = "/usr/local/bin/gog",
) -> None:
    if not sheet_id or not leads:
        return

    values = [lead.to_row() for lead in leads]
    cmd = [
        gog_bin,
        "sheets",
        "append",
        sheet_id,
        f"{tab_name}!A:K",
        "--values-json",
        json.dumps(values),
        "--insert",
        "INSERT_ROWS",
    ]

    if account:
        cmd.extend(["--account", account])

    subprocess.run(cmd, check=True, capture_output=True, text=True)
