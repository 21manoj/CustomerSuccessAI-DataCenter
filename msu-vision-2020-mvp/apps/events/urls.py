from django.urls import path

from apps.events import views

app_name = "events"

urlpatterns = [
    path("", views.EventListView.as_view(), name="list"),
    path("<int:pk>/", views.EventDetailView.as_view(), name="detail"),
]
