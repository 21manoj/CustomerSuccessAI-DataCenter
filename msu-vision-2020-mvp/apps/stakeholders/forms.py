from datetime import date

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from apps.stakeholders.models import PendingUserRegistration, UserProfile

User = get_user_model()


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["organization", "stakeholder_type", "jurisdiction", "email_opt_in"]


class NewUserRegistrationForm(forms.ModelForm):
    desired_role_codes = forms.MultipleChoiceField(
        label="Roles desired",
        choices=UserProfile.StakeholderType.choices,
        widget=forms.CheckboxSelectMultiple,
        required=True,
        help_text="Select all that apply. The team will review and assign appropriate access.",
    )

    class Meta:
        model = PendingUserRegistration
        fields = ["full_name", "email", "batch_year", "phone", "address", "linkedin_url"]
        labels = {
            "full_name": "Full name",
            "email": "Email",
            "batch_year": "Batch (year passed out)",
            "phone": "Contact phone",
            "address": "Address",
            "linkedin_url": "LinkedIn profile URL (optional)",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        y = date.today().year
        self.fields["batch_year"].min_value = 1950
        self.fields["batch_year"].max_value = y + 6
        self.fields["batch_year"].widget.attrs.setdefault("placeholder", str(y - 10))
        self.fields["address"].widget.attrs.setdefault("rows", 3)
        self.fields["desired_role_codes"].widget.attrs.setdefault("class", "space-y-2")

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if not email:
            return email
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError(
                "An account with this email already exists. Please sign in instead."
            )
        if PendingUserRegistration.objects.filter(
            email__iexact=email, status=PendingUserRegistration.Status.PENDING
        ).exists():
            raise ValidationError(
                "We already have a pending application for this email. We will contact you soon."
            )
        return email

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.desired_roles = list(self.cleaned_data["desired_role_codes"])
        obj.status = PendingUserRegistration.Status.PENDING
        if commit:
            obj.save()
        return obj
