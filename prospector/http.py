from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import requests


@dataclass
class RequestManager:
    timeout_seconds: int = 10
    max_retries: int = 3
    backoff_seconds: tuple[int, int, int] = (2, 4, 8)

    def get_json(self, url: str, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> dict:
        response = self._request("GET", url, params=params, headers=headers)
        return response.json()

    def get_text(self, url: str, headers: dict[str, str] | None = None) -> str:
        response = self._request("GET", url, headers=headers)
        return response.text

    def head_status(self, url: str, headers: dict[str, str] | None = None) -> int:
        response = self._request("HEAD", url, headers=headers)
        return response.status_code

    def _request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                if method == "GET":
                    resp = requests.get(url, timeout=self.timeout_seconds, **kwargs)
                elif method == "HEAD":
                    resp = requests.head(url, timeout=self.timeout_seconds, **kwargs)
                else:
                    resp = requests.request(method, url, timeout=self.timeout_seconds, **kwargs)
                if resp.status_code in {429, 500, 502, 503, 504}:
                    raise requests.HTTPError(f"retryable status {resp.status_code}", response=resp)
                resp.raise_for_status()
                return resp
            except (requests.RequestException, ValueError) as exc:
                last_error = exc
                if isinstance(exc, requests.ConnectionError) and "NameResolutionError" in str(exc):
                    break
                if attempt >= self.max_retries - 1:
                    break
                delay = self.backoff_seconds[min(attempt, len(self.backoff_seconds) - 1)]
                time.sleep(delay)
        raise RuntimeError(f"Request failed after retries: {url} ({last_error})")
