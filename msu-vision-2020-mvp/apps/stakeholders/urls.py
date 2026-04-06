from django.urls import path

from apps.stakeholders import views

app_name = "stakeholders"

urlpatterns = [
    path("register/", views.NewUserRegistrationView.as_view(), name="new_user_register"),
    path(
        "register/done/",
        views.NewUserRegistrationDoneView.as_view(),
        name="new_user_register_done",
    ),
    path("profile/", views.ProfileUpdateView.as_view(), name="profile"),
]
