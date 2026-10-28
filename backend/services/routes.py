from .. import db
from ..errors import BadRequest, NotFound


def _require_branches(a: str, b: str) -> None:
    if a == b:
        raise BadRequest("Choose two different locations.")
    found = db.read("MATCH (b:Branch) WHERE b.name IN [$a, $b] RETURN count(b) AS n", {"a": a, "b": b})
    if found[0]["n"] != 2:
        raise NotFound("One or both locations were not found.")


def fewest_hops(a: str, b: str) -> dict:
    """G4"""
    _require_branches(a, b)
    rows = db.read(
        """
        MATCH (a:Branch {name: $a}), (b:Branch {name: $b}),
              p = shortestPath((a)-[:ROUTE_TO*]-(b))
        RETURN [n IN nodes(p) | n.name] AS route, length(p) AS hops,
               reduce(d = 0, r IN relationships(p) | d + r.km) AS km
        """,
        {"a": a, "b": b},
    )
    return rows[0] if rows else {"route": [], "hops": None, "km": None}


def fewest_km(a: str, b: str, limit: int = 3) -> list[dict]:
    """G5: simple paths, ordered by total km."""
    _require_branches(a, b)
    return db.read(
        """
        MATCH p = (a:Branch {name: $a})-[:ROUTE_TO*1..5]-(b:Branch {name: $b})
        WHERE ALL(n IN nodes(p) WHERE single(m IN nodes(p) WHERE m = n))
        WITH p, reduce(d = 0, r IN relationships(p) | d + r.km) AS km
        RETURN [n IN nodes(p) | n.name] AS route, length(p) AS hops, km
        ORDER BY km
        LIMIT $limit
        """,
        {"a": a, "b": b, "limit": limit},
    )


def hub_impact(hub: str) -> list[dict]:
    """G6"""
    if not db.read("MATCH (b:Branch {name: $hub}) RETURN b", {"hub": hub}):
        raise NotFound(f"Hub or branch '{hub}' not found.")
    return db.read(
        """
        MATCH (s:Shipment)-[:HAS_EVENT]->(t:TrackingEvent)-[:AT]->(h:Branch {name: $hub}),
              (s)-[:ADDRESSED_TO]->(r:Customer)
        WHERE NOT (t)-[:NEXT]->()
        RETURN s.shipmentId AS shipment, t.status AS status,
               r.firstName + ' ' + r.lastName AS receiver, r.phone AS phone
        ORDER BY shipment
        """,
        {"hub": hub},
    )
