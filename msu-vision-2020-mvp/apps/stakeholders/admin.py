from django.contrib import admin

from apps.stakeholders.models import Organization, PendingUserRegistration, UserProfile, UserStakeholderPersona


@admin.register(PendingUserRegistration)
class PendingUserRegistrationAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "email",
        "batch_year",
        "phone",
        "status",
        "created_at",
    )
    list_filter = ("status", "batch_year")
    search_fields = ("full_name", "email", "phone")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "status",
                    "full_name",
                    "email",
                    "batch_year",
                    "phone",
                    "address",
                    "linkedin_url",
                    "desired_roles",
                    "notes",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "org_type", "jurisdiction")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "stakeholder_type",
        "needs_persona_assignment",
        "organization",
        "jurisdiction",
    )
    list_filter = ("stakeholder_type", "needs_persona_assignment", "jurisdiction")
    search_fields = ("user__username", "user__email")


@admin.register(UserStakeholderPersona)
class UserStakeholderPersonaAdmin(admin.ModelAdmin):
    list_display = ("user", "persona_type", "created_at")
    list_filter = ("persona_type",)
    search_fields = ("user__username", "user__email")
    raw_id_fields = ("user",)
