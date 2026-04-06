from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import FormView, TemplateView, UpdateView

from apps.stakeholders.forms import NewUserRegistrationForm, UserProfileForm
from apps.stakeholders.models import UserProfile


class NewUserRegistrationView(FormView):
    template_name = "stakeholders/new_user_register.html"
    form_class = NewUserRegistrationForm
    success_url = reverse_lazy("stakeholders:new_user_register_done")

    def form_valid(self, form):
        form.save()
        messages.success(
            self.request,
            "Thank you. Your registration request was submitted. Our team will review it and contact you at the email you provided.",
        )
        return super().form_valid(self)


class NewUserRegistrationDoneView(TemplateView):
    template_name = "stakeholders/new_user_register_done.html"


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = UserProfile
    form_class = UserProfileForm
    template_name = "stakeholders/profile_form.html"
    success_url = reverse_lazy("stakeholders:profile")

    def get_object(self, queryset=None):
        return self.request.user.profile

    def form_valid(self, form):
        messages.success(self.request, "Profile updated.")
        return super().form_valid(form)
