from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Lead:
    domain: str
    company: str
    source: str
    evidence_url: str
    pain_quote: str
    support_stack: str = "unknown"
    docs_url: str = ""
    fit_score: int = 0
    date_found: str = field(default_factory=lambda: datetime.now(timezone.utc).date().isoformat())
    status: str = "New"
    notes: str = ""
    b2b_signal_count: int = 0
    small_team_signal_count: int = 0
    keyword_hits: set[str] = field(default_factory=set)
    keyword_variant_hits: set[str] = field(default_factory=set)
    discard_reason: str = ""
    source_item_id: str = ""
    team_size_signal: str = ""
    founder_name: str = ""
    location: str = ""

    def to_row(self) -> list[str | int]:
        return [
            self.date_found,
            self.company,
            self.domain,
            self.source,
            self.evidence_url,
            self.pain_quote,
            self.support_stack,
            self.docs_url,
            self.fit_score,
            self.status,
            self.notes,
        ]
