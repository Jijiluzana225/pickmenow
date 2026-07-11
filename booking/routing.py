from django.urls import re_path

from .consumers import (
    BookingConsumer,
    TrackingConsumer,
    DriverDashboardConsumer,
    CustomerDashboardConsumer,
)




websocket_urlpatterns = [
    re_path(
        r"ws/booking/(?P<booking_id>\d+)/$",
        BookingConsumer.as_asgi()
    ),

    re_path(
        r"ws/tracking/(?P<booking_id>\d+)/$",
        TrackingConsumer.as_asgi()
    ),

    re_path(
        r"ws/driver-dashboard/$",
        DriverDashboardConsumer.as_asgi()
    ),

    re_path(
        r"ws/customer-dashboard/$",
        CustomerDashboardConsumer.as_asgi()
    ),
]