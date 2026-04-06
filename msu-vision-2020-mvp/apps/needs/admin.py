from django.contrib import admin

from apps.needs.models import Need, NeedAttachment


class NeedAttachmentInline(admin.TabularInline):
    model = NeedAttachment
    extra = 0
    readonly_fields = ("uploaded_by", "created_at")


@admin.register(Need)
class NeedAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "funding_model", "target_amount", "target_currency", "created_by")
    list_filter = ("status", "jurisdiction", "scope")
    search_fields = ("title",)
    filter_horizontal = ("matched_donors", "owners")
    inlines = [NeedAttachmentInline]

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        obj = form.instance
        if obj.owners.count() == 0 and obj.created_by_id:
            obj.owners.add(obj.created_by_id)

    def save_formset(self, request, form, formset, change):
        if formset.model is not NeedAttachment:
            return super().save_formset(request, form, formset, change)
        instances = formset.save(commit=False)
        for obj in formset.deleted_objects:
            obj.delete()
        for obj in instances:
            if not obj.uploaded_by_id:
                obj.uploaded_by = request.user
            obj.save()
        formset.save_m2m()
