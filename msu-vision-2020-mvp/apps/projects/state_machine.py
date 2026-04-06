"""Project & milestone lifecycles — architecture §4.2–4.3 (MVP)."""

PROJECT_TRANSITIONS = {
    "proposed": ("pending_governance", "approved", "rejected"),
    "pending_governance": ("approved", "rejected"),
    "approved": ("in_progress", "on_hold"),
    "in_progress": ("on_hold", "completed"),
    "on_hold": ("in_progress",),
    "completed": (),
    "rejected": (),
}

MILESTONE_TRANSITIONS = {
    "pending": ("approved", "cancelled"),
    "approved": ("in_progress", "cancelled"),
    "in_progress": ("done", "overdue"),
    "overdue": ("done",),
    "done": (),
    "cancelled": (),
}


def allowed_project_next(current: str):
    return PROJECT_TRANSITIONS.get(current, ())


def allowed_milestone_next(current: str):
    return MILESTONE_TRANSITIONS.get(current, ())
