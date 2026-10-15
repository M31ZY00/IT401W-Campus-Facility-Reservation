from django.urls import path
from . import views

urlpatterns = [
    path(
        'create/<int:facility_id>/',
        views.create_reservation,
        name='create_reservation'
    ),

    path(
        'my-reservations/',
        views.my_reservations,
        name='my_reservations'
    ),

    path(
        'cancel/<int:reservation_id>/',
        views.cancel_reservation,
        name='cancel_reservation'
    ),
]