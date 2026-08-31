"""Fail-open Redis JSON cache for non-authoritative API state."""

from __future__ import annotations

import json
from typing import Any


class RedisJsonCache:
    """Cache JSON responses and idempotency markers without affecting decisions."""

    def __init__(self, url: str | None) -> None:
        self._client: Any | None = None
        if url:
            try:
                from redis import Redis

                self._client = Redis.from_url(url, decode_responses=True)
            except Exception:
                # Cache availability must never change scoring or policy.
                self._client = None

    def get_json(self, key: str) -> dict[str, Any] | None:
        if self._client is None:
            return None
        try:
            value = self._client.get(key)
            return json.loads(value) if value else None
        except Exception:
            return None

    def set_json(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        if self._client is None:
            return
        try:
            self._client.set(key, json.dumps(value, default=str), ex=ttl_seconds)
        except Exception:
            pass

    def reserve(self, key: str, ttl_seconds: int) -> bool:
        """Reserve an idempotency key; unavailable Redis means no reservation."""
        if self._client is None:
            return True
        try:
            return bool(self._client.set(key, "__IN_PROGRESS__", nx=True, ex=ttl_seconds))
        except Exception:
            return True
