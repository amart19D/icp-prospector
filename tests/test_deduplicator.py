from prospector.deduplicator import Deduplicator
from prospector.models import Lead


def test_deduplicator_blocks_seen() -> None:
    deduper = Deduplicator({"acme.com": "2026-01-01"})
    lead = Lead(domain="acme.com", company="Acme", source="reddit", evidence_url="x", pain_quote="y", fit_score=55)

    new_leads, skipped = deduper.split_new_and_seen([lead], previous_scores={"acme.com": 50})
    assert len(new_leads) == 0
    assert len(skipped) == 1


def test_deduplicator_allows_new() -> None:
    deduper = Deduplicator({})
    lead = Lead(domain="new.com", company="New", source="reddit", evidence_url="x", pain_quote="y", fit_score=55)

    new_leads, skipped = deduper.split_new_and_seen([lead])
    assert len(new_leads) == 1
    assert len(skipped) == 0
