from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.views.generic import DetailView, ListView

from apps.events.models import Event
from apps.funding.visibility import can_record_contribution
from apps.core.permissions import user_stakeholder_codes
from apps.stakeholders.models import UserProfile


class EventListView(LoginRequiredMixin, ListView):
    model = Event
    template_name = "events/event_list.html"
    context_object_name = "events"

    def get_queryset(self):
        qs = Event.objects.select_related("organized_by", "linked_project", "linked_need").prefetch_related(
            "media_items"
        )
        codes = user_stakeholder_codes(self.request.user)
        if self.request.user.is_superuser or codes & {
            UserProfile.StakeholderType.FOUNDATION_ADMIN,
            UserProfile.StakeholderType.FINANCE_CONTROLLER,
            UserProfile.StakeholderType.GOVERNANCE,
            UserProfile.StakeholderType.AUDITOR,
        }:
            return qs
        # Donors, HOD, leads, volunteers: published and beyond
        return qs.filter(
            status__in=[
                Event.Status.PUBLISHED,
                Event.Status.REGISTRATION_OPEN,
                Event.Status.ONGOING,
                Event.Status.COMPLETED,
                Event.Status.ARCHIVED,
            ]
        )


class EventDetailView(LoginRequiredMixin, DetailView):
    model = Event
    template_name = "events/event_detail.html"
    context_object_name = "event"

    def get_queryset(self):
        return Event.objects.select_related("organized_by", "linked_project", "linked_need").prefetch_related(
            "media_items__uploaded_by", "registrations__user"
        )

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        codes = user_stakeholder_codes(self.request.user)
        if self.request.user.is_superuser or codes & {
            UserProfile.StakeholderType.FOUNDATION_ADMIN,
            UserProfile.StakeholderType.FINANCE_CONTROLLER,
            UserProfile.StakeholderType.GOVERNANCE,
            UserProfile.StakeholderType.AUDITOR,
        }:
            return obj
        if obj.status == Event.Status.DRAFT:
            raise Http404()
        return obj

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["can_prefill_contribution"] = can_record_contribution(self.request.user)
        return ctx
