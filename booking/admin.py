from django.contrib import admin
from .models import *

admin.site.register(Booking)
admin.site.register(DriverProfile)
admin.site.register(CustomerProfile)


@admin.register(ServiceLocation)
class ServiceLocationAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "telegram_chat_id",
        "is_active",
    )

    search_fields = ("name",)

    list_filter = ("is_active",)

