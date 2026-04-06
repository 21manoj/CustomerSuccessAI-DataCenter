from django.contrib import admin

from apps.programs.models import Program, ProgramMilestone, ProgramStage, ProgramStageAttachment


class ProgramStageInline(admin.TabularInline):
    model = ProgramStage
    extra = 0
    ordering = ("sequence", "id")


class ProgramMilestoneInline(admin.TabularInline):
    model = ProgramMilestone
    extra = 0
    ordering = ("sequence", "id")
    fk_name = "stage"


class ProgramStageAttachmentInline(admin.TabularInline):
    model = ProgramStageAttachment
    extra = 0
    readonly_fields = ("uploaded_by", "created_at")


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "status", "fund_pool", "start_date", "end_date", "created_at")
    list_filter = ("status",)
    search_fields = ("title", "slug", "description")
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("admins",)
    inlines = [ProgramStageInline]


@admin.register(ProgramStage)
class ProgramStageAdmin(admin.ModelAdmin):
    list_display = ("name", "program", "sequence", "status")
    list_filter = ("status",)
    inlines = [ProgramMilestoneInline, ProgramStageAttachmentInline]


@admin.register(ProgramMilestone)
class ProgramMilestoneAdmin(admin.ModelAdmin):
    list_display = ("name", "stage", "sequence", "owner", "due_date", "completed_at")
    autocomplete_fields = ("owner", "completed_by")


@admin.register(ProgramStageAttachment)
class ProgramStageAttachmentAdmin(admin.ModelAdmin):
    list_display = ("original_filename", "stage", "uploaded_by", "created_at")
