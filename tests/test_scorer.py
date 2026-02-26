from prospector.models import Lead
from prospector.scorer import Scorer


def test_scorer_expected_score() -> None:
    scorer = Scorer(
        {
            "pain_signal_present": 30,
            "b2b_saas_signals": 25,
            "small_team_signals": 20,
            "helpdesk_stack_detected": 15,
            "docs_present": 10,
        }
    )
    lead = Lead(
        domain="acme.com",
        company="Acme",
        source="reddit",
        evidence_url="https://reddit.com/x",
        pain_quote="support is killing me",
    )
    lead.b2b_signal_count = 4
    lead.small_team_signal_count = 1
    lead.support_stack = "intercom"
    lead.docs_url = "https://acme.com/docs"

    assert scorer.score(lead) == 100


def test_scorer_low_score() -> None:
    scorer = Scorer(
        {
            "pain_signal_present": 30,
            "b2b_saas_signals": 25,
            "small_team_signals": 20,
            "helpdesk_stack_detected": 15,
            "docs_present": 10,
        }
    )
    lead = Lead(domain="", company="", source="hn", evidence_url="", pain_quote="")
    assert scorer.score(lead) == 0
