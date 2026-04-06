import os
from decimal import Decimal

from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models

from apps.core.models import TimeStampedModel
from apps.needs.attachments import need_attachment_upload_to


class Need(TimeStampedModel):
    class FundingModel(models.TextChoices):
        POOLED = "pooled", "Pooled"
        ANCHOR = "anchor", "Anchor"

    class Jurisdiction(models.TextChoices):
        INDIA = "india", "India"
        US = "us", "United States"
        BOTH = "both", "Both"

    class Scope(models.TextChoices):
        DEPARTMENT = "department", "Department"
        CROSS_CUTTING = "cross_cutting", "Cross-cutting"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        CATALOGED = "cataloged", "Cataloged"
        PENDING_GOVERNANCE = "pending_governance", "Pending governance"
        MATCHED = "matched", "Matched"
        REJECTED = "rejected", "Rejected"
        CLOSED = "closed", "Closed"

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="needs_created"
    )
    department = models.ForeignKey(
        "stakeholders.Organization",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="needs",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    funding_model = models.CharField(max_length=16, choices=FundingModel.choices, default=FundingModel.POOLED)
    jurisdiction = models.CharField(max_length=16, choices=Jurisdiction.choices, default=Jurisdiction.INDIA)
    scope = models.CharField(max_length=32, choices=Scope.choices, default=Scope.DEPARTMENT)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.DRAFT)
    target_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    target_currency = models.CharField(max_length=8, default="INR")
    requires_governance_approval = models.BooleanField(default=False)
    matched_donors = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="matched_needs"
    )
    owners = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="owned_needs",
        help_text="At least one registered user accountable for this need (governance, delivery).",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("needs:detail", kwargs={"pk": self.pk})


class NeedAttachment(TimeStampedModel):
    """Supporting documents for a need (PDF, Word, Excel) — architecture media pattern, local storage for MVP."""

    need = models.ForeignKey(Need, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(
        upload_to=need_attachment_upload_to,
        validators=[FileExtensionValidator(allowed_extensions=["pdf", "doc", "docx", "xlsx"])],
    )
    original_filename = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="need_attachments_uploaded"
    )

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.original_filename or os.path.basename(self.file.name)
