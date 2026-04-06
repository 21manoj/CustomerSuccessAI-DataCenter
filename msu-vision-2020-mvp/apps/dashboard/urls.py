from django.urls import path

from apps.dashboard import views

app_name = "dashboard"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("projects/rollup/", views.ProjectRollupView.as_view(), name="project_rollup"),
    path("governance/queue/", views.GovernanceQueueView.as_view(), name="governance_queue"),
    path(
        "governance/profiles/upload/",
        views.governance_profile_bulk_upload,
        name="governance_profile_bulk_upload",
    ),
    path(
        "governance/profiles/sample.csv",
        views.governance_profile_sample_csv,
        name="governance_profile_sample_csv",
    ),
]
