from __future__ import annotations

import re

from prospector.models import Lead
from prospector.sources.base import Source
from prospector.utils import short_snippet


class ProductHuntSource(Source):
    def __init__(self, request_manager, requests_per_minute: int = 20, throttle_multiplier: float = 1.0) -> None:
        super().__init__("product_hunt", request_manager, requests_per_minute, throttle_multiplier)

    def fetch(self, keywords: list[str], config: dict) -> list[Lead]:
        leads: list[Lead] = []
        self._wait_for_slot()
        try:
            html = self.request_manager.get_text("https://www.producthunt.com/")
        except RuntimeError as exc:
            self.logger.warning("Product Hunt fetch failed: %s", exc)
            return []

        cards = re.findall(r'href="(/posts/[^"]+)"[^>]*>([^<]+)<', html)
        for href, title in cards[:25]:
            lead = Lead(
                domain="",
                company=title.strip(),
                source="ph",
                evidence_url=f"https://www.producthunt.com{href}",
                pain_quote=short_snippet("Cold outreach opportunity from Product Hunt launch"),
            )
            leads.append(lead)

        return leads
