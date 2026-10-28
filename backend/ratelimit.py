"""Tiny in-memory sliding-window rate limiter (single process; documented in the README)."""
import time
from collections import defaultdict, deque

from .errors import TooManyRequests

_hits: dict[str, deque] = defaultdict(deque)


def check(key: str, limit: int, window: int = 60) -> None:
    now = time.monotonic()
    q = _hits[key]
    while q and now - q[0] > window:
        q.popleft()
    if len(q) >= limit:
        raise TooManyRequests("Too many requests. Please wait a minute and try again.")
    q.append(now)


def reset() -> None:
    _hits.clear()
