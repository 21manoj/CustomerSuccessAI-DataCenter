from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.core.thresholds import need_requires_governance
from apps.needs.attachments import save_need_attachments, validate_need_attachment_files
from apps.needs.forms import NeedForm, NeedMatchForm
from apps.needs.models import Need, NeedAttachment
from apps.needs.state_machine import allowed_next_statuses
from apps.needs.visibility import (
    can_create_project,
    can_edit_need,
    can_match_need,
    can_transition_need,
    filter_needs_for_user,
)
from apps.core.permissions import has_stakeholder_type
from apps.stakeholders.models import UserProfile

User = get_user_model()


class NeedListView(LoginRequiredMixin, ListView):
    model = Need
    template_name = "needs/need_list.html"
    context_object_name = "needs"

    def get_queryset(self):
        return filter_needs_for_user(Need.objects.prefetch_related("owners"), self.request.user)


class NeedDetailView(LoginRequiredMixin, DetailView):
    model = Need
    template_name = "needs/need_detail.html"
    context_object_name = "need"

    def get_queryset(self):
        return filter_needs_for_user(
            Need.objects.prefetch_related("attachments__uploaded_by", "owners"), self.request.user
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["allowed_next"] = allowed_next_statuses(self.object.status)
        ctx["can_edit"] = can_edit_need(self.request.user, self.object)
        ctx["can_transition"] = can_transition_need(self.request.user, self.object)
        ctx["can_create_project"] = can_create_project(self.request.user, self.object)
        ctx["can_match"] = can_match_need(self.request.user)
        return ctx


class NeedCreateView(LoginRequiredMixin, CreateView):
    model = Need
    form_class = NeedForm
    template_name = "needs/need_form.html"
    success_url = reverse_lazy("needs:list")

    def dispatch(self, request, *args, **kwargs):
        if not (
            request.user.is_superuser
            or has_stakeholder_type(
                request.user,
                UserProfile.StakeholderType.HOD,
                UserProfile.StakeholderType.FOUNDATION_ADMIN,
            )
        ):
            messages.error(request, "Only HOD or Foundation Admin can create needs.")
            return redirect("needs:list")
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        prof = getattr(self.request.user, "profile", None)
        if prof:
            if prof.organization_id:
                initial["department"] = prof.organization_id
            if prof.jurisdiction:
                initial["jurisdiction"] = prof.jurisdiction
        initial["owners"] = [self.request.user.pk]
        return initial

    def form_valid(self, form):
        files = self.request.FILES.getlist("attachments")
        try:
            validate_need_attachment_files(files)
        except ValidationError as e:
            form.add_error(None, e)
            return self.form_invalid(form)
        form.instance.created_by = self.request.user
        form.instance.status = Need.Status.DRAFT
        response = super().form_valid(form)
        n = save_need_attachments(self.object, files, self.request.user)
        if n:
            messages.info(self.request, f"Uploaded {n} attachment(s).")
        messages.success(self.request, "Need saved as draft.")
        return response


class NeedUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Need
    form_class = NeedForm
    template_name = "needs/need_form.html"

    def get_queryset(self):
        return filter_needs_for_user(
            Need.objects.prefetch_related("attachments", "owners"), self.request.user
        )

    def test_func(self):
        return can_edit_need(self.request.user, self.get_object())

    def form_valid(self, form):
        files = self.request.FILES.getlist("attachments")
        try:
            validate_need_attachment_files(files)
        except ValidationError as e:
            form.add_error(None, e)
            return self.form_invalid(form)
        response = super().form_valid(form)
        n = save_need_attachments(self.object, files, self.request.user)
        if n:
            messages.success(self.request, f"Need updated; added {n} attachment(s).")
        else:
            messages.success(self.request, "Need updated.")
        return response

    def get_success_url(self):
        return self.object.get_absolute_url()


def need_transition(request, pk):
    need = get_object_or_404(filter_needs_for_user(Need.objects.all(), request.user), pk=pk)
    if request.method != "POST":
        return redirect("needs:detail", pk=pk)
    if not can_transition_need(request.user, need):
        messages.error(request, "Not allowed to change status.")
        return redirect("needs:detail", pk=pk)
    nxt = request.POST.get("next_status")
    allowed = allowed_next_statuses(need.status)
    if nxt not in allowed:
        messages.error(request, "Invalid transition.")
        return redirect("needs:detail", pk=pk)

    if nxt == "cataloged":
        if need_requires_governance(need.target_amount, need.target_currency):
            need.status = Need.Status.PENDING_GOVERNANCE
            messages.info(request, "Routed to governance (amount over threshold).")
        else:
            need.status = Need.Status.CATALOGED
            messages.success(request, "Need cataloged.")
    elif nxt == "matched" and need.status == Need.Status.PENDING_GOVERNANCE:
        need.status = Need.Status.MATCHED
        messages.success(request, "Governance approved — need matched.")
    else:
        need.status = nxt
        messages.success(request, f"Status updated to {need.get_status_display()}.")
    need.save()
    return redirect("needs:detail", pk=pk)


def need_match(request, pk):
    need = get_object_or_404(filter_needs_for_user(Need.objects.all(), request.user), pk=pk)
    if not can_match_need(request.user):
        messages.error(request, "Not allowed.")
        return redirect("needs:detail", pk=pk)
    donors = User.objects.filter(
        Q(profile__stakeholder_type=UserProfile.StakeholderType.DONOR)
        | Q(stakeholder_personas__persona_type=UserProfile.StakeholderType.DONOR),
        is_active=True,
    ).distinct()
    if request.method == "POST":
        form = NeedMatchForm(request.POST, donor_queryset=donors)
        if form.is_valid():
            need.matched_donors.set(form.cleaned_data["donor_ids"])
            messages.success(request, "Donors linked to this need.")
            return redirect("needs:detail", pk=pk)
    else:
        form = NeedMatchForm(donor_queryset=donors, initial={"donor_ids": need.matched_donors.all()})
    return render(request, "needs/need_match.html", {"need": need, "form": form})


def need_attachment_download(request, need_pk, pk):
    need = get_object_or_404(filter_needs_for_user(Need.objects.all(), request.user), pk=need_pk)
    att = get_object_or_404(NeedAttachment.objects.filter(need=need), pk=pk)
    if not att.file:
        raise Http404()
    try:
        fh = att.file.open("rb")
    except FileNotFoundError:
        raise Http404()
    return FileResponse(
        fh,
        as_attachment=True,
        filename=att.original_filename or att.file.name.rsplit("/", 1)[-1],
    )
