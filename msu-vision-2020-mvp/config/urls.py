from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "MSU Vision 2020 Admin"
admin.site.site_title = "MSU2020"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("", include("apps.dashboard.urls")),
    path("stakeholders/", include("apps.stakeholders.urls")),
    path("needs/", include("apps.needs.urls")),
    path("projects/", include("apps.projects.urls")),
    path("funding/", include("apps.funding.urls")),
    path("events/", include("apps.events.urls")),
    path("programs/", include("apps.programs.urls")),
]

if settings.DEBUG:
    from apps.core.views import demo_login

    urlpatterns += [
        path("__dev__/login-demo/", demo_login, name="demo_login"),
        *static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT),
    ]
