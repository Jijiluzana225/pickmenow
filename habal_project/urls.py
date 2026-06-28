from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

def manifest(request):
    return JsonResponse({
        "name": "PickMeNow",
        "short_name": "PickMeNow",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#000000",
        "orientation": "portrait",
        "icons": [
            {
                "src": "/static/icons/icon-192.png",
                "sizes": "192x192",
                "type": "image/png"
            },
            {
                "src": "/static/icons/icon-512.png",
                "sizes": "512x512",
                "type": "image/png"
            }
        ]
    })

urlpatterns = [
    path("admin/", admin.site.urls),
    path("manifest.json", manifest, name="manifest"),
    path("", include("booking.urls")),
]