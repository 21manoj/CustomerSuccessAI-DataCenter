import os

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.programs.attachments import safe_original_name
from apps.programs.forms import (
    ProgramForm,
    ProgramMilestoneForm,
    ProgramStageAttachmentForm,
    ProgramStageForm,
)
from apps.programs.incubation_template import apply_incubation_template
from apps.programs.models import Program, ProgramMilestone, ProgramStage, ProgramStageAttachment
from apps.programs.permissions import can_edit_program, can_manage_programs


class ProgramListView(LoginRequiredMixin, ListView):
    model = Program
    template_name = "programs/program_list.html"
    context_object_name = "programs"

    def get_queryset(self):
        return Program.objects.select_related("fund_pool", "created_by").order_by("-created_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["can_create"] = can_manage_programs(self.request.user)
        return ctx


class ProgramDetailView(LoginRequiredMixin, DetailView):
    model = Program
    template_name = "programs/program_detail.html"
    context_object_name = "program"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return Program.objects.select_related("fund_pool", "created_by").prefetch_related(
            "admins",
            "projects__need",
            "projects__lead",
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        prog = self.object
        stages = (
            ProgramStage.objects.filter(program=prog)
            .prefetch_related(
                "milestones__owner",
                "milestones__completed_by",
                "attachments__uploaded_by",
            )
            .order_by("sequence", "id")
        )
        ctx["stages"] = list(stages)
        ctx["can_edit"] = can_edit_program(self.request.user, prog)
        ctx["attachment_form"] = ProgramStageAttachmentForm(prog)
        ctx["linked_projects"] = prog.projects.select_related("need", "lead").order_by("-created_at")[:50]
        return ctx

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not can_edit_program(request.user, self.object):
            raise Http404()
        if "apply_incubation" in request.POST:
            n = apply_incubation_template(self.object)
            if n:
                messages.success(request, f"Applied incubation sample template ({n} stages). You can edit or reorder them.")
            else:
                messages.info(request, "Template not applied — this program already has stages.")
            return redirect(self.object.get_absolute_url())
        if "upload_attachment" in request.POST:
            form = ProgramStageAttachmentForm(self.object, request.POST, request.FILES)
            if form.is_valid():
                stage = form.cleaned_data["stage"]
                f = form.cleaned_data["file"]
                ProgramStageAttachment.objects.create(
                    stage=stage,
                    file=f,
                    original_filename=safe_original_name(f),
                    uploaded_by=request.user,
                    notes=form.cleaned_data.get("notes") or "",
                )
                messages.success(request, "Attachment uploaded.")
            else:
                for err in form.errors.values():
                    messages.error(request, err.as_text())
            return redirect(self.object.get_absolute_url())
        if "toggle_milestone" in request.POST:
            mid = request.POST.get("milestone_id")
            m = get_object_or_404(ProgramMilestone, pk=mid, stage__program=self.object)
            if m.completed_at:
                m.completed_at = None
                m.completed_by = None
                m.save()
                messages.info(request, f"Milestone “{m.name}” marked not done.")
            else:
                m.completed_at = timezone.now()
                m.completed_by = request.user
                m.save()
                messages.success(request, f"Milestone “{m.name}” marked complete.")
            return redirect(self.object.get_absolute_url())
        return redirect(self.object.get_absolute_url())


class ProgramCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Program
    form_class = ProgramForm
    template_name = "programs/program_form.html"

    def test_func(self):
        return can_manage_programs(self.request.user)

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        self.object.admins.add(self.request.user)
        messages.success(self.request, "Program created. Add stages or apply the incubation sample template.")
        return response

    def get_success_url(self):
        return self.object.get_absolute_url()


class ProgramUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Program
    form_class = ProgramForm
    template_name = "programs/program_form.html"
    slug_url_kwarg = "slug"

    def test_func(self):
        return can_edit_program(self.request.user, self.get_object())

    def get_success_url(self):
        return self.object.get_absolute_url()


class ProgramStageCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = ProgramStage
    form_class = ProgramStageForm
    template_name = "programs/stage_form.html"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.program = get_object_or_404(Program, slug=kwargs["program_slug"])

    def test_func(self):
        self.program = get_object_or_404(Program, slug=self.kwargs["program_slug"])
        return can_edit_program(self.request.user, self.program)

    def form_valid(self, form):
        form.instance.program = self.program
        messages.success(self.request, "Stage added.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["program"] = self.program
        return ctx

    def get_success_url(self):
        return self.program.get_absolute_url()


class ProgramStageUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = ProgramStage
    form_class = ProgramStageForm
    template_name = "programs/stage_form.html"
    pk_url_kwarg = "pk"

    def get_queryset(self):
        return ProgramStage.objects.select_related("program")

    def test_func(self):
        return can_edit_program(self.request.user, self.get_object().program)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["program"] = self.object.program
        return ctx

    def get_success_url(self):
        return self.object.program.get_absolute_url()


class ProgramStageDeleteView(LoginRequiredMixin, UserPassesTestMixin, View):
    def post(self, request, pk):
        stage = get_object_or_404(ProgramStage.objects.select_related("program"), pk=pk)
        if not can_edit_program(request.user, stage.program):
            raise Http404()
        prog_url = stage.program.get_absolute_url()
        stage.delete()
        messages.info(request, "Stage removed.")
        return redirect(prog_url)


class ProgramMilestoneCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = ProgramMilestone
    form_class = ProgramMilestoneForm
    template_name = "programs/milestone_form.html"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.stage = get_object_or_404(ProgramStage.objects.select_related("program"), pk=kwargs["stage_pk"])

    def test_func(self):
        self.stage = get_object_or_404(ProgramStage.objects.select_related("program"), pk=self.kwargs["stage_pk"])
        return can_edit_program(self.request.user, self.stage.program)

    def form_valid(self, form):
        form.instance.stage = self.stage
        messages.success(self.request, "Milestone added.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["stage"] = self.stage
        ctx["program"] = self.stage.program
        return ctx

    def get_success_url(self):
        return self.stage.program.get_absolute_url()


class ProgramMilestoneUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = ProgramMilestone
    form_class = ProgramMilestoneForm
    template_name = "programs/milestone_form.html"
    pk_url_kwarg = "pk"

    def get_queryset(self):
        return ProgramMilestone.objects.select_related("stage__program")

    def test_func(self):
        return can_edit_program(self.request.user, self.get_object().stage.program)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["stage"] = self.object.stage
        ctx["program"] = self.object.stage.program
        return ctx

    def get_success_url(self):
        return self.object.stage.program.get_absolute_url()


class ProgramMilestoneDeleteView(LoginRequiredMixin, UserPassesTestMixin, View):
    def post(self, request, pk):
        m = get_object_or_404(ProgramMilestone.objects.select_related("stage__program"), pk=pk)
        if not can_edit_program(request.user, m.stage.program):
            raise Http404()
        url = m.stage.program.get_absolute_url()
        m.delete()
        messages.info(request, "Milestone removed.")
        return redirect(url)


class ProgramStageAttachmentDownloadView(LoginRequiredMixin, DetailView):
    model = ProgramStageAttachment
    pk_url_kwarg = "pk"

    def get_queryset(self):
        return ProgramStageAttachment.objects.select_related("stage__program")

    def get(self, request, *args, **kwargs):
        att = self.get_object()
        if not att.file:
            raise Http404()
        try:
            f = att.file.open("rb")
        except OSError:
            raise Http404()
        name = att.original_filename or os.path.basename(att.file.name)
        return FileResponse(f, as_attachment=True, filename=name)
