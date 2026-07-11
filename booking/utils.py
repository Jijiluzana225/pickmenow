import math

from datetime import timedelta

from django.utils import timezone

from .models import DriverProfile


def haversine_distance(lat1, lng1, lat2, lng2):
    earth_radius_km = 6371.0

    lat1 = math.radians(float(lat1))
    lng1 = math.radians(float(lng1))
    lat2 = math.radians(float(lat2))
    lng2 = math.radians(float(lng2))

    latitude_difference = lat2 - lat1
    longitude_difference = lng2 - lng1

    value = (
        math.sin(latitude_difference / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(longitude_difference / 2) ** 2
    )

    central_angle = 2 * math.atan2(
        math.sqrt(value),
        math.sqrt(1 - value)
    )

    return earth_radius_km * central_angle


def get_nearest_driver(
    service_location,
    booking_lat,
    booking_lng
):
    active_since = timezone.now() - timedelta(minutes=2)

    drivers = DriverProfile.objects.filter(
        location=service_location,
        is_available=True,
        is_approved=True,
        current_lat__isnull=False,
        current_lng__isnull=False,
        last_location_update__gte=active_since,
    )

    nearest_driver = None
    nearest_distance = None

    for driver in drivers:
        distance = haversine_distance(
            booking_lat,
            booking_lng,
            driver.current_lat,
            driver.current_lng,
        )

        if (
            nearest_distance is None
            or distance < nearest_distance
        ):
            nearest_driver = driver
            nearest_distance = distance

    return nearest_driver, nearest_distance