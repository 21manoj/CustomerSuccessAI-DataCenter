from django.urls import path

from apps.needs import views

app_name = "needs"

urlpatterns = [
    path("", views.NeedListView.as_view(), name="list"),
    path("create/", views.NeedCreateView.as_view(), name="create"),
    path("<int:pk>/", views.NeedDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", views.NeedUpdateView.as_view(), name="edit"),
    path("<int:pk>/transition/", views.need_transition, name="transition"),
    path("<int:pk>/match/", views.need_match, name="match"),
    path(
        "<int:need_pk>/attachments/<int:pk>/download/",
        views.need_attachment_download,
        name="attachment_download",
    ),
]
