import math

from datetime import timedelta

from django.utils import timezone

from .models import DriverProfile


DRIVER_GPS_ACTIVE_MINUTES = 2


def haversine_distance(
    lat1,
    lng1,
    lat2,
    lng2,
):
    """
    Calculate the distance in kilometers between two GPS coordinates.
    """

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

    # Protect against tiny floating-point errors.
    value = min(
        1.0,
        max(
            0.0,
            value,
        ),
    )

    central_angle = 2 * math.atan2(
        math.sqrt(value),
        math.sqrt(1 - value),
    )

    return earth_radius_km * central_angle


def get_driver_gps_active_since(
    active_minutes=DRIVER_GPS_ACTIVE_MINUTES,
):
    """
    Return the oldest allowed GPS update time for a driver to be
    considered currently active.
    """

    return (
        timezone.now()
        - timedelta(minutes=active_minutes)
    )


def driver_has_current_gps(
    driver,
    active_minutes=DRIVER_GPS_ACTIVE_MINUTES,
):
    """
    Return True when the driver has coordinates and the location was
    updated within the allowed number of minutes.
    """

    if (
        driver.current_lat is None
        or driver.current_lng is None
        or driver.last_location_update is None
    ):
        return False

    active_since = get_driver_gps_active_since(
        active_minutes=active_minutes,
    )

    return (
        driver.last_location_update
        >= active_since
    )


def get_driver_gps_status(
    driver,
    active_minutes=DRIVER_GPS_ACTIVE_MINUTES,
):
    """
    Return information about the driver's most recent GPS update.
    """

    if (
        driver.current_lat is None
        or driver.current_lng is None
    ):
        return {
            "status": "no_gps",
            "label": "No GPS",
            "is_current": False,
            "age_seconds": None,
            "age_minutes": None,
            "latitude": None,
            "longitude": None,
            "last_location_update": None,
        }

    if driver.last_location_update is None:
        return {
            "status": "no_update_time",
            "label": "GPS update time unavailable",
            "is_current": False,
            "age_seconds": None,
            "age_minutes": None,
            "latitude": float(driver.current_lat),
            "longitude": float(driver.current_lng),
            "last_location_update": None,
        }

    gps_age = (
        timezone.now()
        - driver.last_location_update
    )

    age_seconds = max(
        0,
        gps_age.total_seconds(),
    )

    age_minutes = (
        age_seconds / 60
    )

    is_current = (
        age_minutes
        <= active_minutes
    )

    return {
        "status": (
            "current"
            if is_current
            else "stale"
        ),
        "label": (
            "Current GPS"
            if is_current
            else "GPS is outdated"
        ),
        "is_current": is_current,
        "age_seconds": age_seconds,
        "age_minutes": age_minutes,
        "latitude": float(driver.current_lat),
        "longitude": float(driver.current_lng),
        "last_location_update": (
            driver.last_location_update
        ),
    }


def get_drivers_with_current_gps(
    service_location=None,
    active_minutes=DRIVER_GPS_ACTIVE_MINUTES,
    approved_only=False,
    available_only=False,
):
    """
    Return drivers whose GPS was updated recently.

    service_location:
        Optional ServiceLocation object.

    approved_only:
        When True, include only approved drivers.

    available_only:
        When True, include only available drivers.
    """

    active_since = get_driver_gps_active_since(
        active_minutes=active_minutes,
    )

    drivers = (
        DriverProfile.objects
        .select_related(
            "user",
            "location",
        )
        .filter(
            user__is_active=True,
            current_lat__isnull=False,
            current_lng__isnull=False,
            last_location_update__isnull=False,
            last_location_update__gte=active_since,
        )
    )

    if service_location is not None:
        drivers = drivers.filter(
            location=service_location,
        )

    if approved_only:
        drivers = drivers.filter(
            is_approved=True,
        )

    if available_only:
        drivers = drivers.filter(
            is_available=True,
        )

    return drivers.order_by(
        "location__name",
        "full_name",
    )


def get_nearest_driver(
    service_location,
    booking_lat,
    booking_lng,
):
    """
    Find the nearest approved and available driver whose GPS was
    updated within the active GPS time limit.
    """

    drivers = get_drivers_with_current_gps(
        service_location=service_location,
        active_minutes=DRIVER_GPS_ACTIVE_MINUTES,
        approved_only=True,
        available_only=True,
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