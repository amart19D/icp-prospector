from __future__ import annotations

from urllib.parse import quote_plus

from prospector.models import Lead
from prospector.sources.base import Source
from prospector.utils import domain_from_url, extract_domain, short_snippet


class RedditSource(Source):
    def __init__(self, request_manager, requests_per_minute: int = 30, throttle_multiplier: float = 1.0) -> None:
        super().__init__("reddit", request_manager, requests_per_minute, throttle_multiplier)

    def fetch(self, keywords: list[str], config: dict) -> list[Lead]:
        subreddits = config["sources"]["reddit"]["subreddits"]
        leads: list[Lead] = []
        seen_urls: set[str] = set()

        for subreddit in subreddits:
            for keyword in keywords:
                self._wait_for_slot()
                url = f"https://www.reddit.com/r/{subreddit}/search.json?q={quote_plus(keyword)}&sort=new&limit=25&restrict_sr=1"
                try:
                    payload = self.request_manager.get_json(url, headers={"User-Agent": "icp-prospector/0.1"})
                except RuntimeError as exc:
                    self.logger.warning("Reddit request failed for r/%s: %s", subreddit, exc)
                    continue

                for child in payload.get("data", {}).get("children", []):
                    data = child.get("data", {})
                    permalink = data.get("permalink", "")
                    if not permalink:
                        continue
                    evidence_url = f"https://www.reddit.com{permalink}"
                    if evidence_url in seen_urls:
                        continue
                    seen_urls.add(evidence_url)

                    title = data.get("title", "")
                    selftext = data.get("selftext", "")
                    quote = short_snippet(f"{title} {selftext}")
                    maybe_domain = extract_domain(selftext) or domain_from_url(data.get("url", ""))
                    if maybe_domain.endswith("reddit.com"):
                        maybe_domain = ""

                    lead = Lead(
                        domain=maybe_domain,
                        company=data.get("author", "unknown"),
                        source="reddit",
                        evidence_url=evidence_url,
                        pain_quote=quote,
                        source_item_id=str(data.get("id", "")),
                    )
                    lead.keyword_hits.add(keyword.lower())
                    leads.append(lead)

        return leads
