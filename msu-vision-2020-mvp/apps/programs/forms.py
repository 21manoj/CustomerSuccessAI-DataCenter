from django import forms

from apps.core.owner_fields import OWNERS_SELECT_ATTRS, active_registered_users_queryset
from apps.programs.attachments import validate_stage_attachment_file
from apps.programs.models import Program, ProgramMilestone, ProgramStage


class ProgramForm(forms.ModelForm):
    class Meta:
        model = Program
        fields = [
            "title",
            "slug",
            "description",
            "status",
            "fund_pool",
            "start_date",
            "end_date",
            "admins",
        ]
        help_texts = {
            "slug": "URL segment (optional — auto-filled from title if left blank).",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["slug"].required = False
        self.fields["fund_pool"].required = False
        self.fields["admins"].queryset = active_registered_users_queryset()
        self.fields["admins"].required = False
        self.fields["admins"].widget.attrs.update(OWNERS_SELECT_ATTRS)
        self.fields["admins"].help_text = "Users who can edit stages, milestones, and stage attachments."


class ProgramStageForm(forms.ModelForm):
    class Meta:
        model = ProgramStage
        fields = ["sequence", "name", "description", "criteria", "status"]


class ProgramMilestoneForm(forms.ModelForm):
    class Meta:
        model = ProgramMilestone
        fields = ["sequence", "name", "criteria", "due_date", "owner"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["owner"].queryset = active_registered_users_queryset()
        self.fields["owner"].required = False


class ProgramStageAttachmentForm(forms.Form):
    stage = forms.ModelChoiceField(queryset=ProgramStage.objects.none())
    file = forms.FileField()
    notes = forms.CharField(max_length=500, required=False, widget=forms.TextInput(attrs={"class": "mt-1 w-full rounded border p-2 text-sm"}))

    def __init__(self, program, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["stage"].queryset = ProgramStage.objects.filter(program=program).order_by("sequence", "id")
        self.fields["file"].widget.attrs.update({"class": "mt-1 block text-sm"})

    def clean_file(self):
        f = self.cleaned_data.get("file")
        validate_stage_attachment_file(f)
        return f
