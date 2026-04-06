from django.contrib import admin

from apps.needs.models import Need
from apps.projects.models import Milestone, Project, ProjectAttachment, ProjectTeam


class ProjectAttachmentInline(admin.TabularInline):
    model = ProjectAttachment
    extra = 0
    readonly_fields = ("uploaded_by", "created_at")


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "need", "program", "lead", "status", "students_impacted", "budget", "budget_currency")
    list_filter = ("status",)
    autocomplete_fields = ("program",)
    filter_horizontal = ("owners",)
    inlines = [ProjectAttachmentInline]

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        obj = form.instance
        if obj.owners.count() == 0:
            if obj.lead_id:
                obj.owners.add(obj.lead_id)
            elif obj.need_id:
                cb = Need.objects.filter(pk=obj.need_id).values_list("created_by_id", flat=True).first()
                if cb:
                    obj.owners.add(cb)

    def save_formset(self, request, form, formset, change):
        if formset.model is not ProjectAttachment:
            return super().save_formset(request, form, formset, change)
        instances = formset.save(commit=False)
        for obj in formset.deleted_objects:
            obj.delete()
        for obj in instances:
            if not obj.uploaded_by_id:
                obj.uploaded_by = request.user
            obj.save()
        formset.save_m2m()


@admin.register(Milestone)
class MilestoneAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "project",
        "status",
        "sequence",
        "due_date",
        "next_tranche_budget_percent",
        "tranche_governance_status",
    )
    list_filter = ("status", "tranche_governance_status")
    search_fields = ("title", "project__title")
    filter_horizontal = ("owners",)
    raw_id_fields = ("project", "assigned_to")

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        obj = form.instance
        if obj.owners.count() == 0:
            if obj.assigned_to_id:
                obj.owners.add(obj.assigned_to_id)
            elif obj.project_id:
                lead = Project.objects.filter(pk=obj.project_id).values_list("lead_id", flat=True).first()
                if lead:
                    obj.owners.add(lead)


@admin.register(ProjectTeam)
class ProjectTeamAdmin(admin.ModelAdmin):
    list_display = ("project", "user", "role")
