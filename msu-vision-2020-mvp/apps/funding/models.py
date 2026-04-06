from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


def _to_usd(amount: Decimal, currency: str) -> Decimal:
    currency = (currency or "USD").upper()
    rates = getattr(settings, "MVP_EXCHANGE_RATES_TO_USD", {"USD": "1", "INR": "0.012"})
    rate = Decimal(str(rates.get(currency, "1")))
    return (amount or Decimal("0")) * rate


class FundPool(TimeStampedModel):
    class Jurisdiction(models.TextChoices):
        INDIA = "india", "India CSR pool"
        US = "us", "US 501(c)(3) pool"

    jurisdiction = models.CharField(max_length=8, choices=Jurisdiction.choices)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["jurisdiction", "name"]

    def __str__(self):
        return self.name


class Contribution(TimeStampedModel):
    class JurisdictionOrigin(models.TextChoices):
        INDIA = "india", "India"
        US = "us", "United States"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        PLEDGED = "pledged", "Pledged"
        RECEIVED = "received", "Received"
        ALLOCATED = "allocated", "Allocated"
        UTILIZED = "utilized", "Utilized"
        CANCELLED = "cancelled", "Cancelled"

    donor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="contributions"
    )
    project = models.ForeignKey(
        "projects.Project", on_delete=models.SET_NULL, null=True, blank=True, related_name="contributions"
    )
    fund_pool = models.ForeignKey(
        FundPool, on_delete=models.SET_NULL, null=True, blank=True, related_name="contributions"
    )
    event = models.ForeignKey(
        "events.Event", on_delete=models.SET_NULL, null=True, blank=True, related_name="contributions"
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="contributions_recorded"
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=8, default="USD")
    amount_usd = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    jurisdiction_origin = models.CharField(max_length=16, choices=JurisdictionOrigin.choices)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PLEDGED)
    pledge_date = models.DateField(null=True, blank=True)
    received_date = models.DateField(null=True, blank=True)
    receipt_sent = models.BooleanField(
        default=False,
        help_text="Tax/acknowledgment receipt emailed or posted to donor.",
    )
    receipt_sent_date = models.DateField(
        null=True,
        blank=True,
        help_text="When the receipt was sent (optional).",
    )
    communication_capture_url = models.URLField(
        max_length=2048,
        blank=True,
        help_text="Optional link to stored correspondence (e.g. S3 object URL).",
    )
    volunteer_lead = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contributions_volunteer_lead",
        help_text="Volunteer or project lead stewarding this donor relationship (e.g. HNI).",
    )
    reference_number = models.CharField(max_length=128, blank=True)
    notes = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        self.amount_usd = _to_usd(self.amount, self.currency)
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.donor} — {self.amount} {self.currency}"


class Expense(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PENDING_GOVERNANCE = "pending_governance", "Pending governance"
        APPROVED = "approved", "Approved"
        DISBURSED = "disbursed", "Disbursed"
        REJECTED = "rejected", "Rejected"

    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="expenses")
    fund_pool = models.ForeignKey(FundPool, on_delete=models.PROTECT, related_name="expenses")
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="expenses_requested"
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="expenses_approved",
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=8, default="INR")
    amount_usd = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0"))
    description = models.TextField()
    expense_date = models.DateField()
    receipt_reference = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.PENDING)
    requires_governance_approval = models.BooleanField(default=False)
    owners = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="owned_expenses",
        help_text="Registered users accountable for this expense / approval thread (e.g. requester + finance).",
    )

    def save(self, *args, **kwargs):
        self.amount_usd = _to_usd(self.amount, self.currency)
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-expense_date", "-id"]

    def __str__(self):
        return f"{self.project.title}: {self.amount} {self.currency}"
