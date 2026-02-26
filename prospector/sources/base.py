from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod

from prospector.http import RequestManager
from prospector.models import Lead


class Source(ABC):
    def __init__(
        self,
        name: str,
        request_manager: RequestManager,
        requests_per_minute: int = 20,
        throttle_multiplier: float = 1.0,
    ) -> None:
        self.name = name
        self.request_manager = request_manager
        self.requests_per_minute = max(1, int(requests_per_minute))
        self.throttle_multiplier = max(1.0, float(throttle_multiplier))
        self.logger = logging.getLogger(f"prospector.sources.{name}")
        self._request_gap_seconds = (60.0 / self.requests_per_minute) * self.throttle_multiplier
        self._last_request_time = 0.0

    @abstractmethod
    def fetch(self, keywords: list[str], config: dict) -> list[Lead]:
        raise NotImplementedError

    def _wait_for_slot(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self._request_gap_seconds:
            time.sleep(self._request_gap_seconds - elapsed)
        self._last_request_time = time.monotonic()

    def safe_fetch(self, keywords: list[str], config: dict) -> list[Lead]:
        try:
            return self.fetch(keywords, config)
        except Exception as exc:  # noqa: BLE001
            self.logger.warning("source failed: %s", exc)
            return []
