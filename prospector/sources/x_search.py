from __future__ import annotations

import json
import subprocess
import tempfile
import os

from prospector.models import Lead
from prospector.sources.base import Source
from prospector.utils import domain_from_url, extract_domain, short_snippet

X_SCRIPT_PATH = "/root/.openclaw/workspace/skills/x-search/scripts/x_search_smart.py"


class XSearchSource(Source):
    def __init__(self, request_manager, requests_per_minute: int = 20, throttle_multiplier: float = 1.0) -> None:
        super().__init__("x", request_manager, requests_per_minute, throttle_multiplier)

    def fetch(self, keywords: list[str], config: dict) -> list[Lead]:
        leads: list[Lead] = []
        seen_urls: set[str] = set()

        for keyword in keywords:
            self._wait_for_slot()
            with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
                out_path = tf.name
            try:
                cmd = [
                    "python3",
                    X_SCRIPT_PATH,
                    "--query",
                    keyword,
                    "--max",
                    "20",
                    "--no-retweets",
                    "--out",
                    out_path,
                ]
                subprocess.run(cmd, check=True, capture_output=True, text=True)
                with open(out_path) as f:
                    payload = json.load(f)
            except (subprocess.CalledProcessError, FileNotFoundError) as exc:
                self.logger.warning("X script failed for keyword '%s': %s", keyword, exc)
                continue
            except (json.JSONDecodeError, OSError) as exc:
                self.logger.warning("X script output parse failed for keyword '%s': %s", keyword, exc)
                continue
            finally:
                if os.path.exists(out_path):
                    os.unlink(out_path)

            items = payload if isinstance(payload, list) else payload.get("results", payload.get("tweets", []))
            for item in items:
                url = item.get("url") or item.get("tweet_url") or ""
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                text = item.get("text") or item.get("full_text") or ""
                profile = item.get("profile_url") or ""
                website = item.get("website") or ""
                maybe_domain = extract_domain(website) or extract_domain(text) or domain_from_url(profile)
                if maybe_domain.endswith("x.com") or maybe_domain.endswith("twitter.com"):
                    maybe_domain = ""

                lead = Lead(
                    domain=maybe_domain,
                    company=item.get("username") or item.get("author") or "unknown",
                    source="x",
                    evidence_url=url,
                    pain_quote=short_snippet(text),
                    source_item_id=str(item.get("id") or ""),
                )
                lead.keyword_hits.add(keyword.lower())
                leads.append(lead)

        return leads
