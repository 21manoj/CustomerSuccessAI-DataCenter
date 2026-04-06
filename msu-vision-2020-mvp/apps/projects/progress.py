from django.db.models import Sum


def calculate_project_progress(project):
    """Architecture §6.4 — weighted or equal milestone progress."""
    milestones = project.milestones.exclude(status="cancelled")
    if not milestones.exists():
        return 0

    total_weight = milestones.aggregate(s=Sum("weight_percent"))["s"] or 0
    if total_weight and total_weight > 0:
        done_weight = milestones.filter(status="done").aggregate(s=Sum("weight_percent"))["s"] or 0
        return int((done_weight / total_weight) * 100)

    total = milestones.count()
    done = milestones.filter(status="done").count()
    return int((done / total) * 100) if total else 0
