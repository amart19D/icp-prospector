import requests

from prospector.enricher import Enricher
from prospector.http import RequestManager
from prospector.models import Lead


class FakeResponse:
    def __init__(self, text: str, status_code: int = 200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError("bad status")

    def json(self):
        return {}


def test_enricher_detects_stack(monkeypatch) -> None:
    def fake_get(url, timeout=10, **kwargs):
        return FakeResponse("Intercom dashboard API integrations pricing founder small team", 200)

    def fake_head(url, timeout=10, **kwargs):
        if url.endswith("/docs"):
            return FakeResponse("", 200)
        return FakeResponse("", 404)

    monkeypatch.setattr(requests, "get", fake_get)
    monkeypatch.setattr(requests, "head", fake_head)

    enricher = Enricher(RequestManager(timeout_seconds=10))
    lead = Lead(domain="acme.com", company="Acme", source="reddit", evidence_url="x", pain_quote="y")
    enricher.enrich(lead)

    assert lead.support_stack == "intercom"
    # docs_url check removed — _find_docs_url was dropped (4 HEAD reqs per lead, too expensive)
    assert lead.docs_url == ""
    assert lead.b2b_signal_count >= 3
