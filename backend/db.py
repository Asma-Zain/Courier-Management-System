"""Neo4j driver singleton plus small read/write helpers (managed transactions)."""
from typing import Any, Callable

from neo4j import GraphDatabase

from . import config

_driver = None


def get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            config.NEO4J_URI, auth=(config.NEO4J_USERNAME, config.NEO4J_PASSWORD)
        )
    return _driver


def close_driver() -> None:
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None


def clean(value: Any) -> Any:
    """Make Neo4j temporal values JSON friendly."""
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if hasattr(value, "iso_format"):      # neo4j.time.DateTime / Time
        return value.iso_format()
    if hasattr(value, "isoformat"):       # neo4j.time.Date
        return value.isoformat()
    return value


def read(query: str, params: dict | None = None) -> list[dict]:
    def work(tx):
        return [clean(r.data()) for r in tx.run(query, params or {})]
    with get_driver().session(database=config.NEO4J_DATABASE) as session:
        return session.execute_read(work)


def write(work: Callable[[Any], Any]) -> Any:
    """Run work(tx) in one write transaction. Use run(tx, query, params) inside it."""
    with get_driver().session(database=config.NEO4J_DATABASE) as session:
        return session.execute_write(work)


def run(tx, query: str, params: dict | None = None) -> list[dict]:
    return [clean(r.data()) for r in tx.run(query, params or {})]
