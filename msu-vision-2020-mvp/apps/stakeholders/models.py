from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.core.models import TimeStampedModel


class Organization(TimeStampedModel):
    class OrgType(models.TextChoices):
        CORPORATE = "corporate", "Corporate"
        DEPARTMENT = "department", "Department"
        CSR_PARTNER = "csr_partner", "CSR partner"
        GOVT = "govt", "Government"

    class Jurisdiction(models.TextChoices):
        INDIA = "india", "India"
        US = "us", "United States"
        OTHER = "other", "Other"

    name = models.CharField(max_length=255)
    org_type = models.CharField(max_length=32, choices=OrgType.choices, default=OrgType.DEPARTMENT)
    jurisdiction = models.CharField(max_length=16, choices=Jurisdiction.choices, default=Jurisdiction.INDIA)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class UserProfile(TimeStampedModel):
    class StakeholderType(models.TextChoices):
        FOUNDATION_ADMIN = "foundation_admin", "Foundation Admin"
        HOD = "hod", "HOD / Dean"
        DONOR = "donor", "Donor"
        PROJECT_LEAD = "project_lead", "Project Lead"
        VOLUNTEER = "volunteer", "Volunteer"
        FINANCE_CONTROLLER = "finance_controller", "Finance Controller"
        GOVERNANCE = "governance", "Governance Team"
        AUDITOR = "auditor", "Auditor"

    class Jurisdiction(models.TextChoices):
        INDIA = "india", "India"
        US = "us", "United States"
        OTHER = "other", "Other"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    organization = models.ForeignKey(
        Organization, on_delete=models.SET_NULL, null=True, blank=True, related_name="members"
    )
    stakeholder_type = models.CharField(
        max_length=32, choices=StakeholderType.choices, default=StakeholderType.VOLUNTEER
    )
    jurisdiction = models.CharField(max_length=16, choices=Jurisdiction.choices, default=Jurisdiction.INDIA)
    email_opt_in = models.BooleanField(default=False)
    needs_persona_assignment = models.BooleanField(
        default=False,
        help_text="True when imported or created without confirmed personas — show in governance roster until cleared.",
    )

    def persona_codes(self):
        """Effective RBAC persona codes (multi-persona). Empty when flagged and no links yet."""
        codes = set(self.user.stakeholder_personas.values_list("persona_type", flat=True))
        if codes:
            return codes
        if self.needs_persona_assignment:
            return set()
        return {self.stakeholder_type}

    def persona_display(self) -> str:
        """Comma-separated labels for UI."""
        labels = []
        choice_map = dict(self.StakeholderType.choices)
        for code in sorted(self.persona_codes()):
            labels.append(choice_map.get(code, code))
        if not labels:
            return "Persona not identified"
        return ", ".join(labels)

    def __str__(self):
        return f"{self.user.get_username()} ({self.get_stakeholder_type_display()})"


class UserStakeholderPersona(TimeStampedModel):
    """A user may have several stakeholder personas (governance, donor, volunteer, …)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="stakeholder_personas",
    )
    persona_type = models.CharField(max_length=32, choices=UserProfile.StakeholderType.choices)

    class Meta:
        ordering = ["user_id", "persona_type"]
        constraints = [
            models.UniqueConstraint(fields=["user", "persona_type"], name="uniq_user_stakeholder_persona"),
        ]

    def __str__(self):
        return f"{self.user_id}: {self.persona_type}"


class PendingUserRegistration(TimeStampedModel):
    """Alumni / new visitor application before an account is provisioned (reviewed in Admin)."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    full_name = models.CharField(max_length=255)
    email = models.EmailField(db_index=True)
    batch_year = models.PositiveSmallIntegerField(
        help_text="Year you graduated / passed out (batch).",
    )
    phone = models.CharField(max_length=32, help_text="Contact phone number.")
    address = models.TextField(help_text="Mailing or contact address.")
    linkedin_url = models.URLField(
        blank=True,
        help_text="Optional public LinkedIn profile URL.",
    )
    desired_roles = models.JSONField(
        default=list,
        help_text="List of stakeholder role codes requested (e.g. donor, volunteer).",
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    notes = models.TextField(blank=True, help_text="Internal notes (admin only).")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "pending user registration"
        verbose_name_plural = "pending user registrations"

    def __str__(self):
        return f"{self.full_name} <{self.email}> ({self.get_status_display()})"


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)
