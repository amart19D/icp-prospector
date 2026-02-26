from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from prospector.models import Lead
from prospector.scorer import Scorer


def generate_markdown_report(
    output_path: str,
    started_at: datetime,
    ended_at: datetime,
    source_counts: dict[str, int],
    kept_leads: list[Lead],
    discarded_reasons: dict[str, int],
) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    duration = (ended_at - started_at).total_seconds()
    high = [lead for lead in kept_leads if Scorer.band(lead.fit_score) == "High"]
    medium = [lead for lead in kept_leads if Scorer.band(lead.fit_score) == "Medium"]
    low_count = sum(1 for lead in kept_leads if Scorer.band(lead.fit_score) == "Low")

    top_5 = sorted(kept_leads, key=lambda l: l.fit_score, reverse=True)[:5]

    lines = [
        "# ICP Prospector Last Run Report",
        "",
        f"Run timestamp: {ended_at.astimezone(timezone.utc).isoformat()}",
        f"Duration seconds: {duration:.2f}",
        "",
        "## Sources",
        "",
    ]

    for source, count in sorted(source_counts.items()):
        lines.append(f"- {source}: {count}")

    lines.extend(
        [
            "",
            "## Score Distribution",
            "",
            f"- High (70-100): {len(high)}",
            f"- Medium (40-69): {len(medium)}",
            f"- Low (0-39): {low_count}",
            "",
            "## Top 5 Leads",
            "",
            "| Company | Score | Pain Quote | Source |",
            "|---|---:|---|---|",
        ]
    )

    for lead in top_5:
        quote = lead.pain_quote.replace("|", " ")[:120]
        lines.append(f"| {lead.company} | {lead.fit_score} | {quote} | {lead.source} |")

    lines.extend([
        "",
        "## Discards",
        "",
        f"Total discarded: {sum(discarded_reasons.values())}",
    ])

    for reason, count in sorted(discarded_reasons.items()):
        lines.append(f"- {reason}: {count}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
