from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def index(request):
    customer = request.user.customer_profile

    return render(request, "booking/index.html", {
        "customer": customer
    })


from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .models import Booking


@login_required(login_url="driver_login")
def dashboard(request):

    if not hasattr(request.user, "driver_profile"):
        return redirect("driver_login")

    driver = request.user.driver_profile

    if not driver.is_available:
        return render(request, "booking/driver_dashboard_locked.html", {
            "driver": driver
        })

    has_active_booking = Booking.objects.filter(
        driver=driver,
        status="accepted"
    ).exists()

    bookings = Booking.objects.filter(
        status="pending",
        driver__isnull=True
    ).order_by("-created_at")

    return render(request, "booking/dashboard.html", {
        "bookings": bookings,
        "driver": driver,
        "has_active_booking": has_active_booking
    })


from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from .models import Booking
import math

@login_required
def create_booking(request):

    if request.method == "POST":

        customer = request.user.customer_profile

        distance_km = float(request.POST.get("distance_km", 0))
        tip = float(request.POST.get("tip") or 0)

        # Fare computation
        base_fare = 25
        per_km = 8

        fare = math.ceil(base_fare + (distance_km * per_km))

        booking = Booking.objects.create(

            customer=customer,

            customer_name=customer.full_name,
            contact_number=customer.contact_number,

            origin=request.POST.get("origin"),
            destination=request.POST.get("destination"),

            origin_lat=float(request.POST.get("origin_lat")),
            origin_lng=float(request.POST.get("origin_lng")),

            destination_lat=float(request.POST.get("destination_lat")),
            destination_lng=float(request.POST.get("destination_lng")),

            distance_km=distance_km,

            tip=tip,

            instructions=request.POST.get("instructions"),

            fare=fare
        )

        message = f"""
🛵 <b>New Booking Alert</b>

👤 <b>Customer:</b> {booking.customer_name}
📞 <b>Contact:</b> {booking.contact_number}

📍 <b>Pickup:</b> {booking.origin}
🏁 <b>Destination:</b> {booking.destination}

📏 <b>Distance:</b> {booking.distance_km} KM
💰 <b>Fare:</b> ₱{booking.fare}
🎁 <b>Tip:</b> ₱{booking.tip}
💵 <b>Total:</b> ₱{booking.total_amount}

📝 <b>Instructions:</b> {booking.instructions or "None"}

https://www.pickmenow.online/dashboard/


"""

        send_telegram_message(message)

        return redirect("index")

    return redirect("index")



from django.shortcuts import render, get_object_or_404
from .models import Booking

@login_required(login_url="driver_login")
def booking_map(request, id):
    booking = get_object_or_404(Booking, id=id)
    return render(request, "booking/booking_map.html", {
        "booking": booking
    })


from django.shortcuts import get_object_or_404, redirect
from .models import Booking
@login_required(login_url="driver_login")
def navigate_to_origin(request, id):
    booking = get_object_or_404(Booking, id=id)

    url = (
        "https://www.google.com/maps/dir/?api=1"
        f"&destination={booking.origin_lat},{booking.origin_lng}"
        "&travelmode=driving"
    )

    return redirect(url)

from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import login
from .models import CustomerProfile

def customer_register(request):

    if request.method == "POST":

        full_name = request.POST.get("full_name")
        contact_number = request.POST.get("contact_number")
        address = request.POST.get("address")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")
        profile_picture = request.FILES.get("profile_picture")

        if not profile_picture:
            return render(request, "booking/customer_register.html", {
                "error": "Profile picture is required.",
                "full_name": full_name,
                "contact_number": contact_number,
                "address": address,
            })

        if password != confirm_password:
            return render(request, "booking/customer_register.html", {
                "error": "Password and Confirm Password do not match.",
                "full_name": full_name,
                "contact_number": contact_number,
                "address": address,
                "focus_password": True,
            })

        if User.objects.filter(username=contact_number).exists():
            return render(request, "booking/customer_register.html", {
                "error": "Contact number is already registered.",
                "full_name": full_name,
                "contact_number": contact_number,
                "address": address,
            })

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
            profile_picture=profile_picture
        )

        login(request, user)
        return redirect("index")

    return render(request, "booking/customer_register.html")

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from .models import CustomerProfile


def customer_login(request):

    if request.user.is_authenticated:
        return redirect("booking")

    if request.method == "POST":

        contact_number = request.POST["contact_number"]
        password = request.POST["password"]

        user = authenticate(
            username=contact_number,
            password=password
        )

        if user is not None:

            # Allow only customers
            if hasattr(user, "customer_profile"):
                login(request, user)
                return redirect("index")
            else:
                return render(request, "booking/customer_login.html", {
                    "error": "This account is not a customer account."
                })

        return render(request, "booking/customer_login.html", {
            "error": "Invalid contact number or password."
        })

    return render(request, "booking/customer_login.html")


from django.contrib.auth import logout


def customer_logout(request):

    logout(request)

    return redirect("customer_login")


from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .models import Booking


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
        tip = request.POST.get("tip") or 0
        booking.tip = Decimal(tip)
        booking.save()

    return redirect("customer_dashboard")

from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from .models import DriverProfile
from django.http import HttpResponse


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
                "error": "Profile picture is required.",
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

        return HttpResponse("""
        <script>
            alert("Registration successful!\\n\\nWait for the call of the Admin to activate your account.");
            window.location.href = "/customer-login/";
        </script>
        """)

    return render(request, "booking/driver_register.html")


from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login


def driver_login(request):

    if request.user.is_authenticated:
        if hasattr(request.user, "driver_profile"):
            return redirect("dashboard")
        return redirect("index")

    if request.method == "POST":

        contact_number = request.POST.get("contact_number")
        password = request.POST.get("password")

        user = authenticate(
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
                return redirect("dashboard")

            return render(request, "booking/driver_login.html", {
                "error": "This account is not a driver account."
            })

        return render(request, "booking/driver_login.html", {
            "error": "Invalid contact number or password."
        })

    return render(request, "booking/driver_login.html")


from django.contrib.auth import logout


def driver_logout(request):
    logout(request)
    return redirect("customer_login")


from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .models import CustomerProfile


@login_required
def customer_profile_update(request):

    customer = request.user.customer_profile

    if request.method == "POST":

        full_name = request.POST.get("full_name")
        contact_number = request.POST.get("contact_number")
        address = request.POST.get("address")
        profile_picture = request.FILES.get("profile_picture")

        if CustomerProfile.objects.filter(contact_number=contact_number).exclude(id=customer.id).exists():
            return render(request, "booking/customer_profile_update.html", {
                "customer": customer,
                "error": "Contact number is already used by another account."
            })

        customer.full_name = full_name
        customer.contact_number = contact_number
        customer.address = address

        if profile_picture:
            customer.profile_picture = profile_picture

        customer.save()

        request.user.username = contact_number
        request.user.first_name = full_name
        request.user.save()

        return redirect("customer_dashboard")

    return render(request, "booking/customer_profile_update.html", {
        "customer": customer
    })


from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required


@login_required(login_url="driver_login")
def driver_profile_update(request):

    if not hasattr(request.user, "driver_profile"):
        return redirect("driver_login")

    driver = request.user.driver_profile

    if request.method == "POST":

        contact_number = request.POST.get("contact_number")

        # Check if another driver already uses this contact number
        if DriverProfile.objects.exclude(id=driver.id).filter(contact_number=contact_number).exists():
            return render(request, "booking/driver_profile_update.html", {
                "driver": driver,
                "error": "Contact number is already in use."
            })

        driver.full_name = request.POST.get("full_name")
        driver.contact_number = contact_number
        driver.motorcycle_model = request.POST.get("motorcycle_model")
        driver.plate_number = request.POST.get("plate_number")
        driver.license_number = request.POST.get("license_number")

        if request.POST.get("is_available"):
            driver.is_available = True
        else:
            driver.is_available = False

        if request.FILES.get("profile_picture"):
            driver.profile_picture = request.FILES["profile_picture"]

        driver.save()

        # Update Django User account
        request.user.first_name = driver.full_name
        request.user.username = driver.contact_number
        request.user.save()

        return redirect("dashboard")

    return render(request, "booking/driver_profile_update.html", {
        "driver": driver
    })


from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


@login_required(login_url="driver_login")
def toggle_driver_availability(request):

    if not hasattr(request.user, "driver_profile"):
        return redirect("driver_login")

    if request.method == "POST":
        driver = request.user.driver_profile
        driver.is_available = request.POST.get("is_available") == "on"
        driver.save()

    return redirect(request.META.get("HTTP_REFERER", "dashboard"))

from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db import transaction
from .models import Booking
from .sms import send_sms


@login_required(login_url="driver_login")
def accept_booking(request, booking_id):

    if not hasattr(request.user, "driver_profile"):
        return redirect("driver_login")

    driver = request.user.driver_profile

    if Booking.objects.filter(driver=driver, status="accepted").exists():
        return redirect("dashboard")

    if request.method == "POST":

        with transaction.atomic():

            booking = get_object_or_404(
                Booking.objects.select_for_update(),
                id=booking_id,
                status="pending",
                driver__isnull=True
            )

            booking.driver = driver
            booking.status = "accepted"
            booking.assigned_at = timezone.now()
            booking.accepted_at = timezone.now()
            booking.save()

            driver.is_available = False
            driver.save()

        message = (
            f"Good day {booking.customer_name}!\n\n"
            f"Your PickMeNow booking has been accepted. Your Ride is on the way.\n\n"
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

    return redirect("driver_accepted_bookings")


from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from .models import Booking

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


from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .models import Booking


@login_required(login_url="driver_login")
def driver_accepted_bookings(request):

    if not hasattr(request.user, "driver_profile"):
        return redirect("driver_login")

    driver = request.user.driver_profile

    bookings = Booking.objects.filter(
        driver=driver,
        status="accepted"
    ).order_by("-accepted_at", "-assigned_at", "-created_at")

    return render(request, "booking/driver_accepted_bookings.html", {
        "driver": driver,
        "bookings": bookings
    })


from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from .models import Booking

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


from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.db.models import Sum
from .models import Booking


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


import requests
from django.conf import settings


def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"

    data = {
        "chat_id": settings.TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }

    try:
        requests.post(url, data=data, timeout=10)
    except requests.RequestException:
        pass
