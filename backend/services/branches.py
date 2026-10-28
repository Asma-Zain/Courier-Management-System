import time

from .. import db

_cache: tuple[float, list] | None = None
TTL = 300


def list_branches() -> list[dict]:
    global _cache
    if _cache and time.monotonic() - _cache[0] < TTL:
        return _cache[1]
    rows = db.read(
        "MATCH (b:Branch) RETURN b.branchId AS branchId, b.name AS name, b.kind AS kind, b.city AS city "
        "ORDER BY b.branchId"
    )
    _cache = (time.monotonic(), rows)
    return rows
