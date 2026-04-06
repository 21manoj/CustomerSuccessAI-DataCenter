from datetime import date


def timeline_bounds(milestones):
    """Return (min_date, max_date) for Gantt scale; default span if empty."""
    today = date.today()
    dates = []
    for m in milestones:
        dates.extend([m.start_date, m.due_date])
    if not dates:
        return today, today
    return min(dates), max(dates)


def timeline_rows(project, milestones=None):
    """
    Build rows for template: each milestone with left%/width% on a shared scale.
    Architecture §6.5.1 — horizontal bars between start and due.
    If ``milestones`` is provided (e.g. prefetched list), use it to avoid an extra query.
    """
    if milestones is None:
        milestones = list(
            project.milestones.exclude(status="cancelled")
            .select_related("assigned_to")
            .order_by("sequence", "id")
        )
    else:
        milestones = [m for m in milestones if m.status != "cancelled"]
        milestones.sort(key=lambda m: (m.sequence, m.pk))
    start_d, end_d = timeline_bounds(milestones)
    span = (end_d - start_d).days + 1
    if span < 1:
        span = 1
    today = date.today()

    rows = []
    for m in milestones:
        offset_start = (m.start_date - start_d).days
        bar_days = max(1, (m.due_date - m.start_date).days + 1)
        rows.append(
            {
                "milestone": m,
                "left_pct": 100 * offset_start / span,
                "width_pct": min(100, 100 * bar_days / span),
            }
        )

    return {
        "rows": rows,
        "range_start": start_d,
        "range_end": end_d,
        "span_days": span,
        "today": today,
        "today_offset_pct": 100 * max(0, min(span - 1, (today - start_d).days)) / span if span else 0,
    }
