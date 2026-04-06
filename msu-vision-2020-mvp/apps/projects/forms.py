import os

from django import forms
from django.utils.text import get_valid_filename

from apps.core.owner_fields import OWNERS_SELECT_ATTRS, active_registered_users_queryset
from apps.core.thresholds import project_requires_governance
from apps.projects.attachments import validate_milestone_proof_file
from apps.programs.models import Program
from apps.projects.models import Milestone, Project


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            "title",
            "description",
            "program",
            "lead",
            "owners",
            "funding_model",
            "budget",
            "budget_currency",
            "start_date",
            "target_end_date",
            "students_impacted",
        ]

    def __init__(self, *args, need=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["lead"].required = False
        self.fields["owners"].queryset = active_registered_users_queryset()
        self.fields["owners"].label = "Owners"
        self.fields["owners"].help_text = "At least one registered user accountable for this project."
        self.fields["owners"].widget.attrs.update(OWNERS_SELECT_ATTRS)
        self.fields["program"].required = False
        self.fields["program"].queryset = Program.objects.exclude(status=Program.Status.ARCHIVED).order_by(
            "title"
        )
        self.fields["program"].help_text = "Optional long-running program (incubation, etc.). Leave blank for standalone projects."
        self._need = need
        if self._need is None and self.instance.pk and getattr(self.instance, "need_id", None):
            self._need = self.instance.need
        self.fields["title"].help_text = (
            "Starts as the approved need's title so needs and projects stay aligned; change only if you need a distinct label."
        )
        self.fields["students_impacted"].required = False

    def clean_title(self):
        title = (self.cleaned_data.get("title") or "").strip()
        if not title and self._need:
            title = self._need.title.strip()
        if not title:
            raise forms.ValidationError("Title is required (defaults to the need title if left blank).")
        return title

    def clean_owners(self):
        owners = self.cleaned_data.get("owners")
        if not owners:
            raise forms.ValidationError("Select at least one owner from registered users.")
        return owners

    def save(self, commit=True):
        obj = super().save(commit=False)
        if self._need and not (obj.title or "").strip():
            obj.title = self._need.title
        obj.requires_governance_approval = project_requires_governance(obj.budget, obj.budget_currency)
        if commit:
            obj.save()
            self.save_m2m()
        return obj


class MilestoneForm(forms.ModelForm):
    class Meta:
        model = Milestone
        fields = [
            "title",
            "description",
            "assigned_to",
            "owners",
            "start_date",
            "due_date",
            "sequence",
            "weight_percent",
            "status",
            "next_tranche_budget_percent",
            "completion_proof",
            "completion_notes",
        ]

    def __init__(self, *args, project=None, **kwargs):
        inst = kwargs.get("instance")
        self._previous_status = inst.status if inst and getattr(inst, "pk", None) else None
        super().__init__(*args, **kwargs)
        self.fields["assigned_to"].required = False
        self.fields["assigned_to"].label = "Milestone lead"
        self.fields["owners"].queryset = active_registered_users_queryset()
        self.fields["owners"].label = "Owners"
        self.fields["owners"].help_text = "At least one registered user accountable for this milestone."
        self.fields["owners"].widget.attrs.update(OWNERS_SELECT_ATTRS)
        self.fields["sequence"].help_text = "Suggested next sequence and dates from existing milestones; adjust as needed."
        self.fields["next_tranche_budget_percent"].label = "Next funding tranche (% of project budget)"
        self.fields["next_tranche_budget_percent"].help_text = (
            "Share of total project budget gated by this milestone. When > 0, completion proof is required to mark done; "
            "governance must release the tranche before it counts toward funded %."
        )
        self.fields["completion_proof"].label = "Completion proof document"
        self.fields["completion_proof"].help_text = (
            "Photo, PDF, or report proving milestone delivery. Required before marking complete if tranche % > 0."
        )
        self.fields["completion_proof"].required = False

    def clean_completion_proof(self):
        f = self.cleaned_data.get("completion_proof")
        if f:
            validate_milestone_proof_file(f)
        return f

    def clean(self):
        cleaned = super().clean()
        status = cleaned.get("status")
        tr = cleaned.get("next_tranche_budget_percent")
        if tr is None:
            tr = 0
        proof = cleaned.get("completion_proof")
        has_existing_proof = bool(self.instance.pk and self.instance.completion_proof)
        if status == Milestone.Status.DONE and tr > 0:
            if not proof and not has_existing_proof:
                raise forms.ValidationError(
                    "Upload a completion proof document before marking this milestone done when a funding tranche % is set."
                )
        return cleaned

    def clean_owners(self):
        owners = self.cleaned_data.get("owners")
        if not owners:
            raise forms.ValidationError("Select at least one owner from registered users.")
        return owners

    def save(self, commit=True):
        inst = super().save(commit=False)
        f = self.cleaned_data.get("completion_proof")
        if f:
            inst.completion_proof_original_filename = get_valid_filename(os.path.basename(f.name)) or "proof"
        if commit:
            if inst.status == Milestone.Status.DONE:
                tr = inst.next_tranche_budget_percent or 0
                became_done = self._previous_status != Milestone.Status.DONE
                if tr > 0 and became_done:
                    inst.tranche_governance_status = Milestone.TrancheGovernance.AWAITING_GOVERNANCE
                elif tr <= 0 and became_done:
                    inst.tranche_governance_status = Milestone.TrancheGovernance.NOT_APPLICABLE
            inst.save()
            self.save_m2m()
        return inst
