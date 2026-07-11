from django.urls import reverse
from django.http import HttpResponse, JsonResponse, FileResponse, Http404
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum
from decimal import Decimal
from datetime import timedelta
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import math
import requests

from .models import Booking, CustomerProfile, DriverProfile, ServiceLocation
from .sms import send_sms


@login_required(login_url="customer_login")
def index(request):
    if hasattr(request.user, "customer_profile"):
        customer = request.user.customer_profile

        if not customer.location:
            return redirect("choose_customer_location")

        return render(request, "booking/index.html", {
            "customer": customer
        })

    if hasattr(request.user, "driver_profile"):
        return redirect("dashboard")

    return redirect("customer_login")

@login_required(login_url="driver_login")
def dashboard(request):
    if not hasattr(request.user, "driver_profile"):
        return redirect("driver_login")

    driver = request.user.driver_profile

    if not driver.location:
        return redirect("choose_driver_location")

    if not driver.is_available:
        return render(
            request,
            "booking/driver_dashboard_locked.html",
            {
                "driver": driver
            }
        )

    has_active_booking = Booking.objects.filter(
        driver=driver,
        status="accepted"
    ).exists()

    now = timezone.now()

    bookings = Booking.objects.filter(
        status="pending",
        driver__isnull=True,
        location=driver.location
    ).select_related(
        "priority_driver",
        "customer",
    ).order_by("-created_at")

    for booking in bookings:
        # Active whenever the one-minute deadline has not expired.
        priority_window_active = (
            booking.priority_until is not None
            and booking.priority_until > now
        )

        booking.is_priority_driver = (
            booking.priority_driver_id is not None
            and booking.priority_driver_id == driver.id
        )

        # During the first minute:
        # - only the nearest driver can accept;
        # - if no nearest driver was found, nobody can accept.
        #
        # After one minute, all eligible drivers can accept.
        booking.can_accept = (
            not has_active_booking
            and driver.is_available
            and (
                not priority_window_active
                or booking.is_priority_driver
            )
        )

        if priority_window_active and not booking.is_priority_driver:
            booking.wait_seconds = max(
                1,
                math.ceil(
                    (
                        booking.priority_until - now
                    ).total_seconds()
                )
            )
        else:
            booking.wait_seconds = 0

    return render(
        request,
        "booking/dashboard.html",
        {
            "bookings": bookings,
            "driver": driver,
            "has_active_booking": has_active_booking,
            "server_time": now,
        }
    )

from decimal import Decimal, InvalidOperation
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.utils import timezone

from .models import Booking
from .utils import get_nearest_driver


@login_required
def create_booking(request):
    if request.method != "POST":
        return redirect("index")

    if not hasattr(request.user, "customer_profile"):
        return redirect("customer_login")

    customer = request.user.customer_profile

    if not customer.location:
        return redirect("choose_customer_location")

    try:
        distance_km = float(request.POST.get("distance_km", 0))
        tip = Decimal(request.POST.get("tip") or "0")

        origin_lat = float(request.POST.get("origin_lat"))
        origin_lng = float(request.POST.get("origin_lng"))
        destination_lat = float(request.POST.get("destination_lat"))
        destination_lng = float(request.POST.get("destination_lng"))

    except (TypeError, ValueError, InvalidOperation):
        return redirect("index")

    origin = request.POST.get("origin", "").strip()
    destination = request.POST.get("destination", "").strip()
    instructions = request.POST.get("instructions", "").strip()

    if not origin or not destination or distance_km <= 0:
        return redirect("index")

    if tip < 0:
        tip = Decimal("0.00")

    base_fare = Decimal("25.00")
    per_km = Decimal("8.00")

    calculated_fare = (
        base_fare
        + Decimal(str(distance_km)) * per_km
    )

    fare = Decimal(
        math.ceil(calculated_fare)
    ).quantize(Decimal("0.01"))

    nearest_driver, nearest_distance = get_nearest_driver(
        service_location=customer.location,
        booking_lat=origin_lat,
        booking_lng=origin_lng,
    )

    now = timezone.now()

    booking = Booking.objects.create(
        customer=customer,
        customer_name=customer.full_name,
        contact_number=customer.contact_number,
        location=customer.location,
        origin=origin,
        destination=destination,
        origin_lat=origin_lat,
        origin_lng=origin_lng,
        destination_lat=destination_lat,
        destination_lng=destination_lng,
        distance_km=distance_km,
        tip=tip,
        instructions=instructions or None,
        fare=fare,
        status="pending",

        # Nearest recently active driver.
        priority_driver=nearest_driver,

        # Always create a one-minute priority window.
        priority_until=now + timedelta(minutes=1),
    )

    message = f"""
🛵 <b>New Booking Alert</b>

📍 <b>Area:</b> {booking.location.name if booking.location else "No Location"}

👤 <b>Customer:</b> {booking.customer_name}
📞 <b>Contact:</b> {booking.contact_number}

📍 <b>Pickup:</b> {booking.origin}
🏁 <b>Destination:</b> {booking.destination}

📏 <b>Distance:</b> {booking.distance_km:.2f} KM
💰 <b>Fare:</b> ₱{booking.fare}
🎁 <b>Tip:</b> ₱{booking.tip}
💵 <b>Total:</b> ₱{booking.total_amount}

📝 <b>Instructions:</b> {booking.instructions or "None"}

https://www.pickmenow.online/dashboard/
"""

    if booking.location and booking.location.telegram_chat_id:
        send_telegram_message(
            booking.location.telegram_chat_id,
            message
        )

    return redirect("customer_dashboard")


@login_required(login_url="driver_login")
def booking_map(request, id):
    booking = get_object_or_404(Booking, id=id)
    return render(request, "booking/booking_map.html", {
        "booking": booking
    })


@login_required(login_url="driver_login")
def navigate_to_origin(request, id):
    booking = get_object_or_404(Booking, id=id)

    url = (
        "https://www.google.com/maps/dir/?api=1"
        f"&destination={booking.origin_lat},{booking.origin_lng}"
        "&travelmode=driving"
    )

    return redirect(url)


def customer_register(request):
    locations = ServiceLocation.objects.filter(is_active=True).order_by("name")

    if request.method == "POST":
        full_name = request.POST.get("full_name")
        contact_number = request.POST.get("contact_number")
        address = request.POST.get("address")
        location_id = request.POST.get("location")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")
        profile_picture = request.FILES.get("profile_picture")

        context = {
            "full_name": full_name,
            "contact_number": contact_number,
            "address": address,
            "selected_location": location_id,
            "locations": locations,
        }

        if not profile_picture:
            context["error"] = "Profile picture is required."
            return render(request, "booking/customer_register.html", context)

        if not location_id:
            context["error"] = "Please select your location."
            return render(request, "booking/customer_register.html", context)

        try:
            location = ServiceLocation.objects.get(id=location_id, is_active=True)
        except ServiceLocation.DoesNotExist:
            context["error"] = "Selected location is invalid."
            return render(request, "booking/customer_register.html", context)

        if password != confirm_password:
            context["error"] = "Password and Confirm Password do not match."
            context["focus_password"] = True
            return render(request, "booking/customer_register.html", context)

        if User.objects.filter(username=contact_number).exists():
            context["error"] = "Contact number is already registered."
            return render(request, "booking/customer_register.html", context)

        user = User.objects.create_user(
            username=contact_number,
            password=password,
            first_name=full_name
        )

        CustomerProfile.objects.create(
            user=user,
            full_name=full_name,
            contact_number=contact_number,
            address=address,
            location=location,
            profile_picture=profile_picture
        )

        login(request, user)
        return redirect("index")

    return render(request, "booking/customer_register.html", {
        "locations": locations
    })


def customer_login(request):
    if request.user.is_authenticated:
        if hasattr(request.user, "customer_profile"):
            if not request.user.customer_profile.location:
                return redirect("choose_customer_location")

        return redirect("index")

    if request.method == "POST":
        contact_number = request.POST.get("contact_number")
        password = request.POST.get("password")

        user = authenticate(
            request,
            username=contact_number,
            password=password
        )

        if user is not None:
            if hasattr(user, "customer_profile"):
                login(request, user)

                if not user.customer_profile.location:
                    return redirect("choose_customer_location")

                return redirect("index")

            return render(request, "booking/customer_login.html", {
                "error": "This account is not a customer account."
            })

        return render(request, "booking/customer_login.html", {
            "error": "Invalid contact number or password."
        })

    return render(request, "booking/customer_login.html")


def customer_logout(request):
    logout(request)
    return redirect("customer_login")


@login_required
def customer_dashboard(request):
    customer = request.user.customer_profile

    bookings = Booking.objects.filter(
        customer=customer
    ).order_by("-created_at")

    return render(request, "booking/customer_dashboard.html", {
        "customer": customer,
        "bookings": bookings
    })


@login_required
def update_booking_tip(request, booking_id):
    customer = request.user.customer_profile

    booking = get_object_or_404(
        Booking,
        id=booking_id,
        customer=customer
    )

    if request.method == "POST":
        old_tip = booking.tip
        new_tip = Decimal(request.POST.get("tip") or 0)
        tip_added = new_tip - old_tip

        booking.tip = new_tip
        booking.save()

        message = f"""
⭐ <b>TIP Update Alert</b>

📍 <b>Area:</b> {booking.location.name if booking.location else "No Location"}

👤 <b>Customer:</b> {booking.customer_name}
📞 <b>Contact:</b> {booking.contact_number}

📍 <b>Pickup:</b> {booking.origin}
🏁 <b>Destination:</b> {booking.destination}

📏 <b>Distance:</b> {booking.distance_km} KM
💰 <b>Fare:</b> ₱{booking.fare}

☕ <b>Previous Tip:</b> ₱{old_tip}
➕ <b>Added Tip:</b> ₱{tip_added}

🎁 <b>New Tip:</b> ₱{new_tip}

💵 <b>Total:</b> ₱{booking.total_amount}

https://www.pickmenow.online/dashboard/
"""

        if booking.location and booking.location.telegram_chat_id:
            send_telegram_message(
                booking.location.telegram_chat_id,
                message
            )

    return redirect("customer_dashboard")


def driver_register(request):
    if request.method == "POST":
        full_name = request.POST.get("full_name")
        contact_number = request.POST.get("contact_number")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")
        motorcycle_model = request.POST.get("motorcycle_model")
        plate_number = request.POST.get("plate_number")
        license_number = request.POST.get("license_number")
        profile_picture = request.FILES.get("profile_picture")

        if not profile_picture:
            return render(request, "booking/driver_register.html", {
                "error": "Please upload your profile picture.",
                "full_name": full_name,
                "contact_number": contact_number,
                "motorcycle_model": motorcycle_model,
                "plate_number": plate_number,
                "license_number": license_number,
            })

        if password != confirm_password:
            return render(request, "booking/driver_register.html", {
                "error": "Passwords do not match.",
                "full_name": full_name,
                "contact_number": contact_number,
                "motorcycle_model": motorcycle_model,
                "plate_number": plate_number,
                "license_number": license_number,
                "focus_password": True,
            })

        if User.objects.filter(username=contact_number).exists():
            return render(request, "booking/driver_register.html", {
                "error": "Contact number is already registered.",
                "full_name": full_name,
                "contact_number": contact_number,
                "motorcycle_model": motorcycle_model,
                "plate_number": plate_number,
                "license_number": license_number,
            })

        user = User.objects.create_user(
            username=contact_number,
            password=password,
            first_name=full_name
        )

        DriverProfile.objects.create(
            user=user,
            full_name=full_name,
            contact_number=contact_number,
            profile_picture=profile_picture,
            motorcycle_model=motorcycle_model,
            plate_number=plate_number,
            license_number=license_number,
            is_available=True,
            is_approved=False
        )

        return HttpResponse(f"""
            <script>
            alert("Registration successful!\\n\\nWait for the call of the Admin to activate your account.");
            window.location.href = "{reverse('customer_login')}";
            </script>
        """)

    return render(request, "booking/driver_register.html")


def driver_login(request):
    if request.user.is_authenticated:
        if hasattr(request.user, "driver_profile"):
            if not request.user.driver_profile.location:
                return redirect("choose_driver_location")

            return redirect("dashboard")

        return redirect("index")

    if request.method == "POST":
        contact_number = request.POST.get("contact_number")
        password = request.POST.get("password")

        user = authenticate(
            request,
            username=contact_number,
            password=password
        )

        if user is not None:
            if hasattr(user, "driver_profile"):
                if not user.driver_profile.is_approved:
                    return render(request, "booking/driver_login.html", {
                        "error": "Your driver account is still waiting for admin approval."
                    })

                login(request, user)

                if not user.driver_profile.location:
                    return redirect("choose_driver_location")

                return redirect("dashboard")

            return render(request, "booking/driver_login.html", {
                "error": "This account is not a driver account."
            })

        return render(request, "booking/driver_login.html", {
            "error": "Invalid contact number or password."
        })

    return render(request, "booking/driver_login.html")


def driver_logout(request):
    logout(request)
    return redirect("customer_login")


@login_required
def customer_profile_update(request):
    customer = request.user.customer_profile
    locations = ServiceLocation.objects.filter(is_active=True).order_by("name")

    if request.method == "POST":
        full_name = request.POST.get("full_name")
        contact_number = request.POST.get("contact_number")
        address = request.POST.get("address")
        location_id = request.POST.get("location")
        profile_picture = request.FILES.get("profile_picture")

        if CustomerProfile.objects.filter(contact_number=contact_number).exclude(id=customer.id).exists():
            return render(request, "booking/customer_profile_update.html", {
                "customer": customer,
                "locations": locations,
                "error": "Contact number is already used by another account."
            })

        if not location_id:
            return render(request, "booking/customer_profile_update.html", {
                "customer": customer,
                "locations": locations,
                "error": "Please select your location."
            })

        try:
            location = ServiceLocation.objects.get(id=location_id, is_active=True)
        except ServiceLocation.DoesNotExist:
            return render(request, "booking/customer_profile_update.html", {
                "customer": customer,
                "locations": locations,
                "error": "Selected location is invalid."
            })

        customer.full_name = full_name
        customer.contact_number = contact_number
        customer.address = address
        customer.location = location

        if profile_picture:
            customer.profile_picture = profile_picture

        customer.save()

        request.user.username = contact_number
        request.user.first_name = full_name
        request.user.save()

        return redirect("customer_dashboard")

    return render(request, "booking/customer_profile_update.html", {
        "customer": customer,
        "locations": locations
    })


@login_required(login_url="driver_login")
def driver_profile_update(request):
    if not hasattr(request.user, "driver_profile"):
        return redirect("driver_login")

    driver = request.user.driver_profile
    locations = ServiceLocation.objects.filter(is_active=True).order_by("name")

    if request.method == "POST":
        contact_number = request.POST.get("contact_number")
        location_id = request.POST.get("location")

        if DriverProfile.objects.exclude(id=driver.id).filter(contact_number=contact_number).exists():
            return render(request, "booking/driver_profile_update.html", {
                "driver": driver,
                "locations": locations,
                "error": "Contact number is already in use."
            })

        if location_id:
            try:
                driver.location = ServiceLocation.objects.get(id=location_id, is_active=True)
            except ServiceLocation.DoesNotExist:
                return render(request, "booking/driver_profile_update.html", {
                    "driver": driver,
                    "locations": locations,
                    "error": "Selected location is invalid."
                })

        driver.full_name = request.POST.get("full_name")
        driver.contact_number = contact_number
        driver.motorcycle_model = request.POST.get("motorcycle_model")
        driver.plate_number = request.POST.get("plate_number")
        driver.license_number = request.POST.get("license_number")
        driver.is_available = request.POST.get("is_available") == "on"

        if request.FILES.get("profile_picture"):
            driver.profile_picture = request.FILES["profile_picture"]

        driver.save()

        request.user.first_name = driver.full_name
        request.user.username = driver.contact_number
        request.user.save()

        return redirect("dashboard")

    return render(request, "booking/driver_profile_update.html", {
        "driver": driver,
        "locations": locations
    })


@login_required(login_url="driver_login")
def toggle_driver_availability(request):
    if not hasattr(request.user, "driver_profile"):
        return redirect("driver_login")

    if request.method == "POST":
        driver = request.user.driver_profile
        driver.is_available = request.POST.get("is_available") == "on"
        driver.save()

    return redirect(request.META.get("HTTP_REFERER", "dashboard"))

@login_required(login_url="driver_login")
def accept_booking(request, booking_id):
    if not hasattr(request.user, "driver_profile"):
        return redirect("driver_login")

    driver = request.user.driver_profile

    if not driver.location:
        return redirect("choose_driver_location")

    if not driver.is_approved or not driver.is_available:
        return redirect("dashboard")

    if request.method != "POST":
        return redirect("dashboard")

    active_statuses = ["accepted"]

    if Booking.objects.filter(
        driver=driver,
        status__in=active_statuses
    ).exists():
        return redirect("dashboard")

    with transaction.atomic():
        booking = get_object_or_404(
            Booking.objects.select_for_update(),
            id=booking_id,
            status="pending",
            driver__isnull=True,
            location=driver.location
        )

        now = timezone.now()

        priority_window_active = (
            booking.priority_until is not None
            and booking.priority_until > now
        )

        is_priority_driver = (
            booking.priority_driver_id is not None
            and booking.priority_driver_id == driver.id
        )

        # While the one-minute window is active,
        # only the saved nearest driver may accept.
        #
        # When priority_driver is None, nobody may accept
        # until the minute expires.
        if priority_window_active and not is_priority_driver:
            return redirect("dashboard")

        if Booking.objects.select_for_update().filter(
            driver=driver,
            status__in=active_statuses
        ).exists():
            return redirect("dashboard")

        booking.driver = driver
        booking.status = "accepted"
        booking.assigned_at = now
        booking.accepted_at = now

        booking.save(
            update_fields=[
                "driver",
                "status",
                "assigned_at",
                "accepted_at",
            ]
        )

        driver.is_available = False
        driver.save(
            update_fields=[
                "is_available"
            ]
        )

    channel_layer = get_channel_layer()

    async_to_sync(channel_layer.group_send)(
        f"booking_{booking.id}",
        {
            "type": "booking_accepted",
            "booking_id": booking.id,
            "driver_name": driver.full_name,
            "contact_number": driver.contact_number,
            "motorcycle_model": driver.motorcycle_model,
            "plate_number": driver.plate_number,
        }
    )

    message = (
        f"Good day {booking.customer_name}!\n\n"
        f"Your PickMeNow booking has been accepted. "
        f"Your ride is on the way.\n\n"
        f"Driver: {driver.full_name}\n"
        f"Contact: {driver.contact_number}\n"
        f"Motorcycle: {driver.motorcycle_model}\n"
        f"Plate No: {driver.plate_number}\n\n"
        f"Pickup: {booking.origin}\n"
        f"Destination: {booking.destination}\n\n"
        f"Ride safely!"
    )

    sms_result = send_sms(
        booking.contact_number,
        message
    )

    print("=" * 60)
    print("SMS SEND RESULT")
    print(sms_result)
    print("=" * 60)
    print(
        "WEBSOCKET SENT TO:",
        f"booking_{booking.id}"
    )

    return redirect("driver_accepted_bookings")

@login_required
def cancel_booking(request, booking_id):
    booking = get_object_or_404(
        Booking,
        id=booking_id,
        customer=request.user.customer_profile
    )

    if request.method == "POST":
        if booking.status in ["pending", "assigned"]:
            booking.status = "cancelled"
            booking.save()

    return redirect("customer_dashboard")


@login_required(login_url="driver_login")
def driver_accepted_bookings(request):
    if not hasattr(request.user, "driver_profile"):
        return redirect("driver_login")

    driver = request.user.driver_profile

    bookings = Booking.objects.filter(
        driver=driver,
        status="accepted"
    ).order_by("-accepted_at", "-assigned_at", "-created_at")

    for booking in bookings:
        booking.can_no_show = (
            booking.status == "accepted"
            and booking.accepted_at
            and timezone.now() >= booking.accepted_at + timedelta(minutes=2)
        )

    return render(request, "booking/driver_accepted_bookings.html", {
        "driver": driver,
        "bookings": bookings
    })


@login_required(login_url="driver_login")
def navigate_to_destination(request, id):
    booking = get_object_or_404(Booking, id=id)

    url = (
        "https://www.google.com/maps/dir/?api=1"
        f"&destination={booking.destination_lat},{booking.destination_lng}"
        "&travelmode=driving"
    )

    return redirect(url)


@login_required(login_url="driver_login")
def complete_booking(request, booking_id):
    if not hasattr(request.user, "driver_profile"):
        return redirect("driver_login")

    driver = request.user.driver_profile

    booking = get_object_or_404(
        Booking,
        id=booking_id,
        driver=driver,
        status="accepted"
    )

    if request.method == "POST":
        booking.status = "completed"
        booking.save()

        driver.is_available = True
        driver.save()

    return redirect("driver_accepted_bookings")


@login_required(login_url="driver_login")
def driver_completed_bookings(request):
    if not hasattr(request.user, "driver_profile"):
        return redirect("driver_login")

    driver = request.user.driver_profile

    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    bookings = Booking.objects.filter(
        driver=driver,
        status="completed"
    )

    if start_date:
        bookings = bookings.filter(created_at__date__gte=start_date)

    if end_date:
        bookings = bookings.filter(created_at__date__lte=end_date)

    bookings = bookings.order_by("-created_at")

    summary = bookings.aggregate(
        total_fare=Sum("fare"),                     
        total_tip=Sum("tip")
    )

    total_fare = summary["total_fare"] or 0
    total_tip = summary["total_tip"] or 0
    grand_total = total_fare + total_tip

    return render(request, "booking/driver_completed_bookings.html", {
        "driver": driver,
        "bookings": bookings,
        "total_fare": total_fare,
        "total_tip": total_tip,
        "grand_total": grand_total,
        "start_date": start_date,
        "end_date": end_date,
    })


def send_telegram_message(chat_id, message):
    if not chat_id:
        return

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"

    data = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
    }

    try:
        requests.post(url, data=data, timeout=10)
    except requests.RequestException:
        pass


@login_required(login_url="driver_login")
def update_driver_location(request):
    if not hasattr(request.user, "driver_profile"):
        return JsonResponse({"success": False})

    if request.method == "POST":
        driver = request.user.driver_profile
        driver.current_lat = request.POST.get("lat")
        driver.current_lng = request.POST.get("lng")
        driver.last_location_update = timezone.now()
        driver.save()

        return JsonResponse({"success": True})

    return JsonResponse({"success": False})


@login_required
def get_driver_location(request, booking_id):
    if not hasattr(request.user, "customer_profile"):
        return JsonResponse({
            "success": False,
            "error": "Customer profile not found."
        })

    booking = get_object_or_404(
        Booking,
        id=booking_id,
        customer=request.user.customer_profile
    )

    if not booking.driver:
        return JsonResponse({
            "success": False,
            "error": "No driver assigned."
        })

    if booking.driver.current_lat is None or booking.driver.current_lng is None:
        return JsonResponse({
            "success": False,
            "error": "Driver location not available yet.",
            "driver_name": booking.driver.full_name,
        })

    return JsonResponse({
        "success": True,
        "driver_name": booking.driver.full_name,
        "lat": booking.driver.current_lat,
        "lng": booking.driver.current_lng,
        "customer_lat": booking.origin_lat,
        "customer_lng": booking.origin_lng,
    })


def download_apk(request):
    apk_path = settings.BASE_DIR / "apk" / "PickMeNow-v1.0.apk"

    if not apk_path.exists():
        raise Http404("APK file not found")

    return FileResponse(
        open(apk_path, "rb"),
        as_attachment=True,
        filename="PickMeNow-v1.0.apk"
    )


@login_required(login_url="driver_login")
def no_show_booking(request, booking_id):
    if not hasattr(request.user, "driver_profile"):
        return redirect("driver_login")

    driver = request.user.driver_profile

    booking = get_object_or_404(
        Booking,
        id=booking_id,
        driver=driver,
        status="accepted"
    )

    if request.method == "POST":
        booking.status = "no_show"
        booking.instructions = "No Show"
        booking.save()

        driver.is_available = True
        driver.save()

    return redirect("driver_accepted_bookings")


@login_required
def choose_customer_location(request):
    profile = request.user.customer_profile
    locations = ServiceLocation.objects.filter(is_active=True).order_by("name")

    if request.method == "POST":
        location_id = request.POST.get("location_id")

        try:
            location = ServiceLocation.objects.get(id=location_id, is_active=True)
        except ServiceLocation.DoesNotExist:
            return render(request, "booking/choose_location.html", {
                "locations": locations,
                "error": "Please select a valid location."
            })

        profile.location = location
        profile.save()

        return redirect("customer_dashboard")

    return render(request, "booking/choose_location.html", {
        "locations": locations
    })


@login_required
def choose_driver_location(request):
    profile = request.user.driver_profile
    locations = ServiceLocation.objects.filter(is_active=True).order_by("name")

    if request.method == "POST":
        location_id = request.POST.get("location_id")

        try:
            location = ServiceLocation.objects.get(id=location_id, is_active=True)
        except ServiceLocation.DoesNotExist:
            return render(request, "booking/choose_location.html", {
                "locations": locations,
                "error": "Please select a valid location."
            })

        profile.location = location
        profile.save()

        return redirect("dashboard")

    return render(request, "booking/choose_location.html", {
        "locations": locations
    })