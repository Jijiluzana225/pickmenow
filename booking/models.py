from django.db import models
from django.contrib.auth.models import User
from cloudinary_storage.storage import MediaCloudinaryStorage


class CustomerProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="customer_profile"
    )

    full_name = models.CharField(max_length=100)

    contact_number = models.CharField(
        max_length=20,
        unique=True
    )

    address = models.TextField(blank=True, null=True)

    profile_picture = models.ImageField(storage=MediaCloudinaryStorage(), upload_to='habal/', blank=False, null=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name


class DriverProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="driver_profile"
    )

    full_name = models.CharField(max_length=100)

    contact_number = models.CharField(
        max_length=20,
        unique=True
    )

    profile_picture = models.ImageField(storage=MediaCloudinaryStorage(), upload_to='habal/', blank=False, null=False)
    

    motorcycle_model = models.CharField(max_length=100)

    plate_number = models.CharField(max_length=30)

    license_number = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )

    is_available = models.BooleanField(default=True)
    is_approved = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    current_lat = models.FloatField(blank=True, null=True)
    current_lng = models.FloatField(blank=True, null=True)
    last_location_update = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.full_name


class Booking(models.Model):

    BOOKING_STATUS = [
        ("pending", "Pending"),
        ("assigned", "Assigned"),
        ("accepted", "Accepted"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    customer = models.ForeignKey(
        CustomerProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bookings"
    )

    customer_name = models.CharField(max_length=100)

    contact_number = models.CharField(max_length=20)

    origin = models.CharField(max_length=255)
    destination = models.CharField(max_length=255)

    origin_lat = models.FloatField()
    origin_lng = models.FloatField()

    destination_lat = models.FloatField()
    destination_lng = models.FloatField()

    distance_km = models.FloatField(default=0)

    tip = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    fare = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    instructions = models.TextField(blank=True, null=True)

    driver = models.ForeignKey(
        DriverProfile,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="bookings"
    )

    status = models.CharField(
        max_length=20,
        choices=BOOKING_STATUS,
        default="pending"
    )

    assigned_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(blank=True, null=True)

    @property
    def total_amount(self):
        return self.fare + self.tip

    def __str__(self):
        return f"{self.customer_name} - {self.origin} to {self.destination}"