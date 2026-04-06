from django.contrib import admin

from apps.events.models import Event, EventMedia, EventRegistration


class EventMediaInline(admin.TabularInline):
    model = EventMedia
    extra = 0


class EventRegistrationInline(admin.TabularInline):
    model = EventRegistration
    extra = 0


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "event_type", "status", "start_datetime", "organized_by")
    list_filter = ("status", "event_type")
    inlines = [EventMediaInline, EventRegistrationInline]


@admin.register(EventMedia)
class EventMediaAdmin(admin.ModelAdmin):
    list_display = ("event", "caption", "media_type", "created_at")


@admin.register(EventRegistration)
class EventRegistrationAdmin(admin.ModelAdmin):
    list_display = ("event", "user", "role", "registered_at", "attended")
