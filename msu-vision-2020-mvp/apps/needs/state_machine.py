"""Need lifecycle — architecture §4.1 (simplified for MVP)."""

NEED_TRANSITIONS = {
    "draft": ("cataloged", "rejected"),
    "cataloged": ("pending_governance", "matched", "rejected"),
    "pending_governance": ("matched", "rejected"),
    "matched": ("closed",),
    "rejected": (),
    "closed": (),
}


def allowed_next_statuses(current: str):
    return NEED_TRANSITIONS.get(current, ())
