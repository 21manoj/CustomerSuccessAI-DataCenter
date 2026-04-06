import os

from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils.text import slugify

from apps.core.models import TimeStampedModel
from apps.programs.attachments import program_stage_attachment_upload_to


class Program(TimeStampedModel):
    """
    Long-lived, repeatable initiative (incubation, scholarships, etc.).
    Optional link to projects via Project.program; most programs stand alone.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PLANNED = "planned", "Planned"
        ACTIVE = "active", "Active"
        CLOSED = "closed", "Closed"
        ARCHIVED = "archived", "Archived"

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=120, unique=True, db_index=True)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    fund_pool = models.ForeignKey(
        "funding.FundPool",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="programs",
        help_text="Optional primary pool for allocations and prizes.",
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="programs_created",
    )
    admins = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="programs_administered",
        help_text="Users who can edit stages, milestones, and attachments for this program.",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not (self.slug or "").strip():
            base = slugify(self.title)[:110] or "program"
            slug = base
            n = 0
            while Program.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                n += 1
                slug = f"{base}-{n}"
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("programs:detail", kwargs={"slug": self.slug})


class ProgramStage(TimeStampedModel):
    class Status(models.TextChoices):
        NOT_STARTED = "not_started", "Not started"
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"

    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name="stages")
    sequence = models.PositiveIntegerField(default=0)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    criteria = models.TextField(
        blank=True,
        help_text="What must be true to complete this stage (admin-defined).",
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.NOT_STARTED)

    class Meta:
        ordering = ["program", "sequence", "id"]

    def __str__(self):
        return f"{self.program.title}: {self.name}"


class ProgramMilestone(TimeStampedModel):
    stage = models.ForeignKey(ProgramStage, on_delete=models.CASCADE, related_name="milestones")
    sequence = models.PositiveIntegerField(default=0)
    name = models.CharField(max_length=255)
    criteria = models.TextField(blank=True)
    due_date = models.DateField(null=True, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="program_milestones_owned",
        help_text="Accountable person for this milestone (shown on program view).",
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="program_milestones_completed",
    )

    class Meta:
        ordering = ["stage", "sequence", "id"]

    def __str__(self):
        return f"{self.stage.name}: {self.name}"


class ProgramStageAttachment(TimeStampedModel):
    stage = models.ForeignKey(ProgramStage, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(
        upload_to=program_stage_attachment_upload_to,
        validators=[
            FileExtensionValidator(allowed_extensions=["pdf", "doc", "docx", "xlsx", "jpg", "jpeg", "png"])
        ],
    )
    original_filename = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="program_stage_attachments_uploaded",
    )
    notes = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.original_filename or os.path.basename(self.file.name)
