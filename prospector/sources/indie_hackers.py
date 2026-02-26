from __future__ import annotations

from urllib.parse import quote_plus

from prospector.models import Lead
from prospector.sources.base import Source
from prospector.utils import domain_from_url, extract_domain, short_snippet


class IndieHackersSource(Source):
    def __init__(self, request_manager, requests_per_minute: int = 20, throttle_multiplier: float = 1.0) -> None:
        super().__init__("indie_hackers", request_manager, requests_per_minute, throttle_multiplier)

    def fetch(self, keywords: list[str], config: dict) -> list[Lead]:
        leads: list[Lead] = []
        seen_urls: set[str] = set()

        for keyword in keywords:
            self._wait_for_slot()
            query = f"site:indiehackers.com {keyword}"
            url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
            try:
                html = self.request_manager.get_text(url, headers={"User-Agent": "icp-prospector/0.1"})
            except RuntimeError as exc:
                self.logger.warning("IH search failed for keyword '%s': %s", keyword, exc)
                continue

            for line in html.splitlines():
                if "result__a" not in line or "href=" not in line:
                    continue
                link = line.split('href="', 1)[1].split('"', 1)[0]
                if "indiehackers.com" not in link or link in seen_urls:
                    continue
                seen_urls.add(link)
                lead = Lead(
                    domain=extract_domain(line) or domain_from_url(link),
                    company="unknown",
                    source="ih",
                    evidence_url=link,
                    pain_quote=short_snippet(keyword),
                )
                lead.keyword_hits.add(keyword.lower())
                leads.append(lead)

        return leads
