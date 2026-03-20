from __future__ import annotations

import time
from typing import Iterator

import requests


class OpenAlexClient:
    def __init__(self, base_url: str, per_page: int, mailto: str, polite_sleep_seconds: float, max_retries: int) -> None:
        self.base_url = base_url
        self.per_page = per_page
        self.mailto = mailto
        self.polite_sleep_seconds = polite_sleep_seconds
        self.max_retries = max_retries
        self.session = requests.Session()

    def _get(self, params: dict) -> dict:
        last_error: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(self.base_url, params=params, timeout=120)
                response.raise_for_status()
                return response.json()
            except Exception as exc:  # pragma: no cover - network retry path
                last_error = exc
                time.sleep(min(3 * (attempt + 1), 15))
        if last_error is None:  # pragma: no cover
            raise RuntimeError("OpenAlex request failed without a captured exception.")
        raise last_error

    def iter_query(self, filter_expression: str) -> Iterator[dict]:
        cursor = "*"
        while cursor:
            params = {
                "filter": filter_expression,
                "per-page": self.per_page,
                "cursor": cursor,
                "mailto": self.mailto,
            }
            payload = self._get(params)
            for row in payload.get("results", []):
                yield row
            cursor = payload.get("meta", {}).get("next_cursor")
            time.sleep(self.polite_sleep_seconds)

