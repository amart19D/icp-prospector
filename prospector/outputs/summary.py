from __future__ import annotations

import json

import requests
from rich.console import Console

from prospector.models import Lead
from prospector.scorer import Scorer


def emit_summary(mode: str, webhook: str, leads: list[Lead], discarded_count: int) -> None:
    high = sum(1 for lead in leads if Scorer.band(lead.fit_score) == "High")
    medium = sum(1 for lead in leads if Scorer.band(lead.fit_score) == "Medium")

    message = (
        f"ICP Prospector: {len(leads)} leads kept, {discarded_count} discarded "
        f"(High={high}, Medium={medium})"
    )

    if mode == "discord" and webhook:
        try:
            requests.post(webhook, json={"content": message}, timeout=8)
        except requests.RequestException:
            Console().print(message)
    else:
        Console().print(message)


def summarize_discard_reasons(discarded: list[Lead]) -> dict[str, int]:
    reasons: dict[str, int] = {}
    for lead in discarded:
        reason = lead.discard_reason or "unknown"
        reasons[reason] = reasons.get(reason, 0) + 1
    return reasons


def reasons_to_text(reasons: dict[str, int]) -> str:
    if not reasons:
        return "none"
    return json.dumps(reasons, sort_keys=True)
