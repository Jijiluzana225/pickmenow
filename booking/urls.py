from django.urls import path
from . import views


urlpatterns = [
    path('', views.index, name='index'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('create-booking/', views.create_booking, name='create_booking'),
    
    path("navigate/<int:id>/", views.navigate_to_origin, name="navigate_to_origin"),
    path("customer/register/", views.customer_register,  name="customer_register" ),
  
    path("customer/login/",views.customer_login, name="customer_login" ),
    path("customer/logout/",views.customer_logout,name="customer_logout"),

    path("customer/dashboard/", views.customer_dashboard, name="customer_dashboard"),
    path("customer/booking/<int:booking_id>/update-tip/", views.update_booking_tip, name="update_booking_tip"),

    path("driver/register/", views.driver_register, name="driver_register"),
    path("driver/login/", views.driver_login, name="driver_login"),

    path("driver/logout/",views.driver_logout,name="driver_logout"),
    path("customer/profile/update/",views.customer_profile_update,name="customer_profile_update"),

    path("driver/profile/update/", views.driver_profile_update, name="driver_profile_update"),

    path("driver/toggle-availability/", views.toggle_driver_availability,name="toggle_driver_availability"),
    path("booking/<int:booking_id>/accept/", views.accept_booking, name="accept_booking"),

    path("booking/<int:booking_id>/cancel/", views.cancel_booking, name="cancel_booking"),

    path("driver/accepted-bookings/",views.driver_accepted_bookings, name="driver_accepted_bookings"),

    path("navigate-destination/<int:id>/", views.navigate_to_destination, name="navigate_to_destination"),
    path("booking/<int:booking_id>/complete/", views.complete_booking, name="complete_booking"),

    path("driver/completed-bookings/",views.driver_completed_bookings, name="driver_completed_bookings"),

    path("driver/update-location/", views.update_driver_location, name="update_driver_location"),
    path("booking/<int:booking_id>/driver-location/", views.get_driver_location, name="get_driver_location"),

    path("download/", views.download_app, name="download_app"),



    
]