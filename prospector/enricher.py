from __future__ import annotations

import re
from urllib.parse import urljoin

from prospector.http import RequestManager
from prospector.models import Lead

SUPPORT_STACKS = ["intercom", "helpscout", "crisp", "zendesk", "freshdesk", "gorgias"]
DOCS_PATHS = ["/docs", "/help", "/support", "/kb"]
B2B_TERMS = ["dashboard", "api", "integrations", "pricing", "team"]
SMALL_TEAM_TERMS = ["indie", "bootstrapped", "solo", "founder", "small team", "just the two of us", "small team of"]
TEAM_PAGES = ["/about", "/team"]


class Enricher:
    def __init__(self, request_manager: RequestManager) -> None:
        self.request_manager = request_manager

    def enrich(self, lead: Lead) -> Lead:
        if not lead.domain:
            return lead

        home_url = self._normalize_home_url(lead.domain)
        try:
            html = self.request_manager.get_text(home_url)
        except RuntimeError:
            return lead

        lower_html = html.lower()
        lead.support_stack = self._detect_support_stack(lower_html)
        lead.b2b_signal_count = self._count_signals(lower_html, B2B_TERMS)
        lead.small_team_signal_count = self._count_signals(lower_html, SMALL_TEAM_TERMS)
        # NOTE: docs URL check removed — 4 HEAD requests per lead is too expensive
        # lead.docs_url = self._find_docs_url(home_url)

        details_text = self._scrape_details_pages(home_url)
        if details_text:
            low_details = details_text.lower()
            lead.small_team_signal_count = max(
                lead.small_team_signal_count,
                self._count_signals(low_details, SMALL_TEAM_TERMS),
            )
            lead.team_size_signal = self._extract_team_size_signal(details_text)
            lead.founder_name = self._extract_founder_name(details_text)
            lead.location = self._extract_location(details_text)

        return lead

    def _normalize_home_url(self, domain: str) -> str:
        if domain.startswith("http://") or domain.startswith("https://"):
            return domain
        return f"https://{domain}"

    def _detect_support_stack(self, html: str) -> str:
        for stack in SUPPORT_STACKS:
            if stack in html:
                return stack
        return "unknown"

    def _find_docs_url(self, home_url: str) -> str:
        for path in DOCS_PATHS:
            docs_url = urljoin(home_url.rstrip("/") + "/", path.lstrip("/"))
            try:
                status = self.request_manager.head_status(docs_url)
            except RuntimeError:
                continue
            if status < 400:
                return docs_url
        return ""

    def _scrape_details_pages(self, home_url: str) -> str:
        chunks: list[str] = []
        for page in TEAM_PAGES:
            url = urljoin(home_url.rstrip("/") + "/", page.lstrip("/"))
            try:
                chunks.append(self.request_manager.get_text(url))
            except RuntimeError:
                continue
        return "\n".join(chunks)

    @staticmethod
    def _count_signals(text: str, terms: list[str]) -> int:
        return sum(1 for term in terms if term in text)

    @staticmethod
    def _extract_team_size_signal(text: str) -> str:
        patterns = [
            r"just the two of us",
            r"small team of\s+\d+",
            r"team of\s+\d+",
            r"solo founder",
        ]
        lowered = text.lower()
        for pattern in patterns:
            match = re.search(pattern, lowered)
            if match:
                return match.group(0)
        return ""

    @staticmethod
    def _extract_founder_name(text: str) -> str:
        patterns = [
            r"founded by\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
            r"founder[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return ""

    @staticmethod
    def _extract_location(text: str) -> str:
        match = re.search(r"based in\s+([A-Z][A-Za-z\s]+)", text)
        if match:
            return match.group(1).strip()
        return ""
