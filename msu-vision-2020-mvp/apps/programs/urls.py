from django.urls import path

from apps.programs import views

app_name = "programs"

urlpatterns = [
    path("", views.ProgramListView.as_view(), name="list"),
    path("new/", views.ProgramCreateView.as_view(), name="create"),
    path("<slug:slug>/", views.ProgramDetailView.as_view(), name="detail"),
    path("<slug:slug>/edit/", views.ProgramUpdateView.as_view(), name="update"),
    path("<slug:program_slug>/stages/new/", views.ProgramStageCreateView.as_view(), name="stage_create"),
    path("stages/<int:pk>/edit/", views.ProgramStageUpdateView.as_view(), name="stage_update"),
    path("stages/<int:pk>/delete/", views.ProgramStageDeleteView.as_view(), name="stage_delete"),
    path("stages/<int:stage_pk>/milestones/new/", views.ProgramMilestoneCreateView.as_view(), name="milestone_create"),
    path("milestones/<int:pk>/edit/", views.ProgramMilestoneUpdateView.as_view(), name="milestone_update"),
    path("milestones/<int:pk>/delete/", views.ProgramMilestoneDeleteView.as_view(), name="milestone_delete"),
    path("attachments/<int:pk>/download/", views.ProgramStageAttachmentDownloadView.as_view(), name="attachment_download"),
]
