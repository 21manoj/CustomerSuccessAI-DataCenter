from django.contrib import admin

from apps.funding.models import Contribution, Expense, FundPool


@admin.register(FundPool)
class FundPoolAdmin(admin.ModelAdmin):
    list_display = ("name", "jurisdiction")


@admin.register(Contribution)
class ContributionAdmin(admin.ModelAdmin):
    list_display = (
        "donor",
        "amount",
        "currency",
        "amount_usd",
        "status",
        "pledge_date",
        "received_date",
        "receipt_sent",
        "volunteer_lead",
        "project",
        "event",
        "recorded_by",
    )
    list_filter = ("status", "jurisdiction_origin", "receipt_sent")


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("project", "amount", "currency", "status", "expense_date", "requested_by")
    list_filter = ("status",)
    filter_horizontal = ("owners",)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        obj = form.instance
        if obj.owners.count() == 0 and obj.requested_by_id:
            obj.owners.add(obj.requested_by_id)
