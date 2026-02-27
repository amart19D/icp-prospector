from prospector.http import RequestManager
from prospector.sources.reddit import RedditSource


class FakeRequestManager(RequestManager):
    def __init__(self):
        super().__init__(timeout_seconds=10)

    def get_json(self, url, params=None, headers=None):
        # pullpush.io format: {"data": [{flat post object}, ...]}
        return {
            "data": [
                {
                    "id": "abc123",
                    "permalink": "/r/SaaS/comments/abc123/help_docs_are_a_mess/",
                    "title": "Help docs are a mess",
                    "selftext": "our support is killing me at acme.com",
                    "author": "founder1",
                    "url": "https://acme.com",
                }
            ]
        }


def test_reddit_source_extracts_lead() -> None:
    source = RedditSource(FakeRequestManager(), requests_per_minute=9999)
    cfg = {"sources": {"reddit": {"subreddits": ["SaaS"]}}}
    leads = source.fetch(["support is killing me"], cfg)

    assert len(leads) == 1
    lead = leads[0]
    assert lead.source == "reddit"
    assert lead.domain == "acme.com"
    assert "help docs" in lead.pain_quote.lower()
