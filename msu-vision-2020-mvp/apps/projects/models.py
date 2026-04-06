import os
from decimal import Decimal

from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models

from apps.core.models import TimeStampedModel
from apps.projects.attachments import milestone_proof_upload_to, project_attachment_upload_to


class Project(TimeStampedModel):
    class FundingModel(models.TextChoices):
        INHERITED = "inherited", "Inherited from need"
        POOLED = "pooled", "Pooled"
        ANCHOR = "anchor", "Anchor"

    class Status(models.TextChoices):
        PROPOSED = "proposed", "Proposed"
        PENDING_GOVERNANCE = "pending_governance", "Pending governance"
        APPROVED = "approved", "Approved"
        IN_PROGRESS = "in_progress", "In progress"
        ON_HOLD = "on_hold", "On hold"
        COMPLETED = "completed", "Completed"
        REJECTED = "rejected", "Rejected"

    need = models.ForeignKey("needs.Need", on_delete=models.PROTECT, related_name="projects")
    lead = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="projects_led"
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    funding_model = models.CharField(max_length=16, choices=FundingModel.choices, default=FundingModel.INHERITED)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.PROPOSED)
    budget = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    budget_currency = models.CharField(max_length=8, default="INR")
    requires_governance_approval = models.BooleanField(default=False)
    start_date = models.DateField(null=True, blank=True)
    target_end_date = models.DateField(null=True, blank=True)
    actual_end_date = models.DateField(null=True, blank=True)
    students_impacted = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Students / residents impacted",
        help_text="Estimated residents / learners served (for impact scorecard). Leave blank if unknown.",
    )
    owners = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="owned_projects",
        help_text="At least one registered user accountable for delivery and approvals.",
    )
    program = models.ForeignKey(
        "programs.Program",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects",
        help_text="Optional link to a long-running program; leave blank for standalone projects.",
    )

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if self.need_id and not (self.title or "").strip():
            self.title = self.need.title
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("projects:detail", kwargs={"pk": self.pk})


class ProjectAttachment(TimeStampedModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(
        upload_to=project_attachment_upload_to,
        validators=[FileExtensionValidator(allowed_extensions=["pdf", "doc", "docx", "xlsx"])],
    )
    original_filename = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="project_attachments_uploaded"
    )

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.original_filename or os.path.basename(self.file.name)


class ProjectTeam(TimeStampedModel):
    class Role(models.TextChoices):
        LEAD = "lead", "Lead"
        VOLUNTEER = "volunteer", "Volunteer"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="team_members")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="project_teams")
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.VOLUNTEER)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [["project", "user"]]


class Milestone(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        IN_PROGRESS = "in_progress", "In progress"
        DONE = "done", "Done"
        OVERDUE = "overdue", "Overdue"
        CANCELLED = "cancelled", "Cancelled"

    class TrancheGovernance(models.TextChoices):
        NOT_APPLICABLE = "not_applicable", "N/A (no tranche)"
        AWAITING_GOVERNANCE = "awaiting_governance", "Awaiting governance release"
        RELEASED = "released", "Tranche released"
        REJECTED = "rejected", "Tranche rejected"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="milestones")
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="milestones"
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    start_date = models.DateField()
    due_date = models.DateField()
    completed_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.PENDING)
    sequence = models.PositiveIntegerField(default=0)
    weight_percent = models.PositiveSmallIntegerField(default=0, help_text="0 = equal weight across milestones")
    completion_notes = models.TextField(blank=True)
    next_tranche_budget_percent = models.PositiveSmallIntegerField(
        default=0,
        help_text="% of total project budget unlocked for the next phase after this milestone is completed "
        "(with proof). Governance must approve before it counts as released. Use 0 if no tranche at this gate.",
    )
    completion_proof = models.FileField(
        upload_to=milestone_proof_upload_to,
        blank=True,
        null=True,
        validators=[
            FileExtensionValidator(allowed_extensions=["pdf", "doc", "docx", "xlsx", "jpg", "jpeg", "png"])
        ],
        help_text="Required before marking complete when a funding tranche % is set. Evidence for governance.",
    )
    completion_proof_original_filename = models.CharField(max_length=255, blank=True)
    tranche_governance_status = models.CharField(
        max_length=32,
        choices=TrancheGovernance.choices,
        default=TrancheGovernance.NOT_APPLICABLE,
    )
    owners = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="owned_milestones",
        help_text="At least one registered user accountable for this milestone.",
    )

    class Meta:
        ordering = ["project", "sequence", "id"]

    def __str__(self):
        return f"{self.project.title}: {self.title}"
