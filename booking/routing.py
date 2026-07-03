from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/booking/(?P<booking_id>\d+)/$", consumers.BookingConsumer.as_asgi()),
]