from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import DatabaseError, transaction
from django.db.models import F

from facilities.models import Facility
from management.models import SystemSetting
from management.audit import record_audit

from .forms import ReservationForm
from .models import Reservation, ReservationChange

from authentication.decorators import basic_user_required

@basic_user_required
def create_reservation(request, facility_id):

    facility = get_object_or_404(
        Facility,
        id=facility_id,
        is_active=True,
        category__is_active=True
    )

    system_setting = SystemSetting.get_current()

    if request.method == 'POST':
        form = ReservationForm(request.POST)
    else:
        form = ReservationForm()

    form.fields['start_time'].help_text = (
        f'Reservations can only be made up to '
        f'{system_setting.advance_booking_days} '
        f'calendar days in advance.'
    )

    form.fields['end_time'].help_text = (
        f'Maximum reservation duration is '
        f'{system_setting.max_booking_hours} hours.'
    )

    if request.method == 'POST':

        if form.is_valid():

            reservation = form.save(commit=False)

            reservation.user = request.user
            reservation.facility = facility
            reservation.status = 'pending'

            try:

                reservation.full_clean()

                reservation.save()

                messages.success(
                    request,
                    'Reservation submitted successfully. '
                    'Please wait for ADMIN approval.'
                )

                return redirect('my_reservations')

            except ValidationError as error:

                form.add_error(
                    None,
                    '; '.join(error.messages)
                )

            except DatabaseError:

                form.add_error(
                    None,
                    'The reservation could not be saved '
                    'due to a database conflict. Please try again.'
                )

    return render(
        request,
        'reservations/create_reservation.html',
        {
            'form': form,
            'facility': facility,
            'system_setting': system_setting
        }
    )


@basic_user_required
def my_reservations(request):

    reservations = Reservation.objects.filter(
        user=request.user
    ).select_related(
        'facility'
    ).order_by('-created_at')

    return render(
        request,
        'reservations/my_reservations.html',
        {
            'reservations': reservations
        }
    )


@basic_user_required
@require_POST
def cancel_reservation(request, reservation_id):

    reservation_reference = get_object_or_404(
        Reservation.objects.only('facility_id'),
        id=reservation_id,
        user=request.user
    )

    try:

        with transaction.atomic():

            Facility.objects.filter(
                pk=reservation_reference.facility_id
            ).update(
                is_active=F('is_active')
            )

            reservation = get_object_or_404(
                Reservation.objects.select_for_update(),
                id=reservation_id,
                user=request.user
            )

            if reservation.status not in ['pending', 'approved']:

                messages.error(
                    request,
                    'This reservation can no longer be cancelled.'
                )

                return redirect('my_reservations')

            if reservation.start_time <= timezone.now():

                messages.error(
                    request,
                    'Reservations cannot be cancelled '
                    'after their scheduled start time.'
                )

                return redirect('my_reservations')

            previous_status = reservation.status

            reservation.status = 'cancelled'

            reservation.save(
                update_fields=['status']
            )

            ReservationChange.objects.create(
                reservation=reservation,
                changed_by=request.user,
                previous_status=previous_status,
                new_status='cancelled',
                previous_start_time=reservation.start_time,
                previous_end_time=reservation.end_time,
                new_start_time=reservation.start_time,
                new_end_time=reservation.end_time,
                reason='Cancelled by the reservation owner.'

            )

            record_audit(
                request,
                'CANCEL',
                reservation,
                (
                    f'Reservation #{reservation.pk} was cancelled '
                    f'by Basic User {request.user.username}. '
                    f'Previous status: {previous_status}. '
                    f'New status: cancelled.'
                )
            )


    except DatabaseError:

        messages.error(
            request,
            'The reservation could not be cancelled '
            'due to a database conflict. Please try again.'
        )

        return redirect('my_reservations')

    messages.success(
        request,
        'Your reservation has been cancelled successfully.'
    )

    return redirect('my_reservations')