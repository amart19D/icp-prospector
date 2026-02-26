from __future__ import annotations

from urllib.parse import quote_plus

from prospector.models import Lead
from prospector.sources.base import Source
from prospector.utils import domain_from_url, extract_domain, short_snippet


class HackerNewsSource(Source):
    def __init__(self, request_manager, requests_per_minute: int = 40, throttle_multiplier: float = 1.0) -> None:
        super().__init__("hacker_news", request_manager, requests_per_minute, throttle_multiplier)

    def fetch(self, keywords: list[str], config: dict) -> list[Lead]:
        leads: list[Lead] = []
        seen_urls: set[str] = set()

        for keyword in keywords:
            self._wait_for_slot()
            url = f"https://hn.algolia.com/api/v1/search?query={quote_plus(keyword)}&tags=story,comment&hitsPerPage=20"
            try:
                payload = self.request_manager.get_json(url)
            except RuntimeError as exc:
                self.logger.warning("HN request failed for keyword '%s': %s", keyword, exc)
                continue

            for hit in payload.get("hits", []):
                item_url = hit.get("url") or ""
                hn_url = f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"
                evidence_url = item_url or hn_url
                if evidence_url in seen_urls:
                    continue
                seen_urls.add(evidence_url)

                text = hit.get("comment_text") or hit.get("story_text") or hit.get("title") or ""
                maybe_domain = domain_from_url(item_url) or extract_domain(text)
                lead = Lead(
                    domain=maybe_domain,
                    company=hit.get("author", "unknown"),
                    source="hn",
                    evidence_url=evidence_url,
                    pain_quote=short_snippet(text),
                    source_item_id=str(hit.get("objectID", "")),
                )
                lead.keyword_hits.add(keyword.lower())
                leads.append(lead)

        return leads
