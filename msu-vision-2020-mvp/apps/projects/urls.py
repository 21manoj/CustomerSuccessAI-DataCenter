from django.urls import path

from apps.projects import views

app_name = "projects"

urlpatterns = [
    path("", views.ProjectListView.as_view(), name="list"),
    path("create/<int:need_id>/", views.ProjectCreateView.as_view(), name="create"),
    path("<int:pk>/", views.ProjectDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", views.ProjectUpdateView.as_view(), name="edit"),
    path("<int:pk>/transition/", views.project_transition, name="transition"),
    path("<int:pk>/timeline/", views.project_timeline_partial, name="timeline_partial"),
    path(
        "<int:pk>/attachments/<int:attachment_pk>/download/",
        views.project_attachment_download,
        name="attachment_download",
    ),
    path("<int:project_id>/milestones/create/", views.MilestoneCreateView.as_view(), name="milestone_create"),
    path("milestones/<int:pk>/edit/", views.MilestoneUpdateView.as_view(), name="milestone_edit"),
    path("milestones/<int:pk>/transition/", views.milestone_transition, name="milestone_transition"),
    path(
        "milestones/<int:pk>/proof/download/",
        views.milestone_proof_download,
        name="milestone_proof_download",
    ),
    path(
        "milestones/<int:pk>/tranche-release/",
        views.milestone_tranche_release,
        name="milestone_tranche_release",
    ),
]
