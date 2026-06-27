from django.urls import path, include
from django.contrib import admin
from django.http import HttpResponse
from django.conf import settings
from pathlib import Path


def service_worker(request):
    sw_path = settings.BASE_DIR / "habal_project" / "static" / "service-worker.js"

    with open(sw_path, "r", encoding="utf-8") as file:
        return HttpResponse(
            file.read(),
            content_type="application/javascript"
        )


urlpatterns = [
    path("admin/", admin.site.urls),
    path("service-worker.js", service_worker, name="service_worker"),
    path("", include("booking.urls")),
]