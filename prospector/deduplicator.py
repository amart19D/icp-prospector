from __future__ import annotations

from prospector.models import Lead


class Deduplicator:
    def __init__(self, seen_domains: dict[str, str], improvement_threshold: int = 15) -> None:
        self.seen_domains = seen_domains
        self.improvement_threshold = improvement_threshold

    def split_new_and_seen(self, leads: list[Lead], previous_scores: dict[str, int] | None = None) -> tuple[list[Lead], list[Lead]]:
        previous_scores = previous_scores or {}
        new_leads: list[Lead] = []
        skipped: list[Lead] = []

        for lead in leads:
            if lead.domain not in self.seen_domains:
                new_leads.append(lead)
                continue

            prior_score = previous_scores.get(lead.domain, 0)
            if lead.fit_score - prior_score > self.improvement_threshold:
                new_leads.append(lead)
            else:
                lead.discard_reason = "already_seen"
                skipped.append(lead)

        return new_leads, skipped

    def mark(self, leads: list[Lead], date_value: str) -> None:
        for lead in leads:
            self.seen_domains.setdefault(lead.domain, date_value)
