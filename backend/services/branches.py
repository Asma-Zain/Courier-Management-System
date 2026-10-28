from .. import db


def list_branches() -> list[dict]:
    return db.read(
        "MATCH (b:Branch) RETURN b.branchId AS branchId, b.name AS name, b.kind AS kind, b.city AS city "
        "ORDER BY b.branchId"
    )
