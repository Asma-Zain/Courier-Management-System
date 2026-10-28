"""Shipment status order. Pure functions, no database access."""
FINAL = {"DELIVERED", "CANCELLED"}

TRANSITIONS = {
    "BOOKED": ["PICKED_UP", "CANCELLED", "DELAYED"],          # CANCELLED only before PICKED_UP
    "PICKED_UP": ["IN_TRANSIT", "DELAYED"],
    "IN_TRANSIT": ["AT_BRANCH", "OUT_FOR_DELIVERY", "DELAYED"],
    "AT_BRANCH": ["IN_TRANSIT", "OUT_FOR_DELIVERY", "DELAYED"],
    "OUT_FOR_DELIVERY": ["DELIVERED", "DELAYED"],
    "DELIVERED": [],
    "CANCELLED": [],
}


def next_statuses(history: list[str]) -> list[str]:
    """Allowed next statuses given the statuses so far (oldest first)."""
    if not history:
        return ["BOOKED"]
    current = history[-1]
    if current in FINAL:
        return []
    if current != "DELAYED":
        return list(TRANSITIONS[current])
    # DELAYED rejoins the chain it interrupted: the last real status, or the step after it.
    last_real = next((s for s in reversed(history) if s != "DELAYED"), "BOOKED")
    allowed = [s for s in TRANSITIONS[last_real] if s != "DELAYED"]
    if last_real != "BOOKED":
        allowed.insert(0, last_real)  # resumed, still in the same state
    return allowed
