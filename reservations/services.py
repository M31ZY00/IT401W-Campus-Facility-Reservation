from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from facilities.models import Facility
from management.audit import record_audit

from .models import Reservation, ReservationChange, EventRecord


ALLOWED_TRANSITIONS = {
    'APPROVE': ('pending', 'approved'),
    'REJECT': ('pending', 'rejected'),
    'CANCEL': ('approved', 'cancelled'),
    'CHECK_IN': ('approved', 'checked_in'),
    'COMPLETE': ('checked_in', 'completed'),
    'NO_SHOW': ('approved', 'no_show'),
}


def update_reservation(request, reservation_id, action, reason=''):
    action = action.upper().strip()
    reason = reason.strip()

    if action not in ALLOWED_TRANSITIONS:
        raise ValidationError('Invalid reservation action.')

    expected_status, new_status = ALLOWED_TRANSITIONS[action]

    if action in ['REJECT', 'CANCEL'] and not reason:
        raise ValidationError('A reason is required for this action.')

    reservation_reference = Reservation.objects.only(
        'facility_id'
    ).get(pk=reservation_id)

    with transaction.atomic():
        Facility.objects.filter(
            pk=reservation_reference.facility_id
        ).update(is_active=F('is_active'))

        reservation = (
            Reservation.objects
            .select_for_update()
            .select_related(
                'facility',
                'facility__category',
                'user'
            )
            .get(pk=reservation_id)
        )

        if reservation.status != expected_status:
            raise ValidationError(
                f'This action requires a reservation '
                f'with status "{expected_status}".'
            )

        previous_status = reservation.status
        now = timezone.now()

        if action == 'APPROVE':
            reservation.status = 'approved'
            reservation.full_clean()

            reservation.decision_by = request.user
            reservation.decision_at = now
            reservation.decision_reason = reason

            reservation.save(
                update_fields=[
                    'status',
                    'decision_by',
                    'decision_at',
                    'decision_reason'
                ]
            )

        elif action == 'REJECT':
            reservation.status = 'rejected'
            reservation.decision_by = request.user
            reservation.decision_at = now
            reservation.decision_reason = reason

            reservation.save(
                update_fields=[
                    'status',
                    'decision_by',
                    'decision_at',
                    'decision_reason'
                ]
            )

        elif action == 'CANCEL':
            if reservation.start_time <= now:
                raise ValidationError(
                    'Cannot cancel a reservation after its scheduled start time.'
                )

            reservation.status = 'cancelled'
            reservation.save(update_fields=['status'])

        elif action == 'CHECK_IN':
            if not (
                reservation.start_time <= now < reservation.end_time
            ):
                raise ValidationError(
                    'Check-in is only allowed during '
                    'the scheduled reservation period.'
                )

            reservation.status = 'checked_in'
            reservation.save(update_fields=['status'])

            event_record, created = EventRecord.objects.get_or_create(
                reservation=reservation
            )

            event_record.actual_start = now
            event_record.checked_in_by = request.user

            event_record.save(
                update_fields=[
                    'actual_start',
                    'checked_in_by'
                ]
            )

        elif action == 'COMPLETE':
            reservation.status = 'completed'
            reservation.save(update_fields=['status'])

            event_record, created = EventRecord.objects.get_or_create(
                reservation=reservation
            )

            event_record.actual_end = now
            event_record.completed_by = request.user

            event_record.save(
                update_fields=[
                    'actual_end',
                    'completed_by'
                ]
            )

        elif action == 'NO_SHOW':
            if now < reservation.end_time:
                raise ValidationError(
                    'No-show can only be recorded '
                    'after the scheduled end time.'
                )

            reservation.status = 'no_show'
            reservation.save(update_fields=['status'])

            event_record, created = EventRecord.objects.get_or_create(
                reservation=reservation
            )

            event_record.no_show_at = now
            event_record.no_show_marked_by = request.user

            event_record.save(
                update_fields=[
                    'no_show_at',
                    'no_show_marked_by'
                ]
            )

        ReservationChange.objects.create(
            reservation=reservation,
            changed_by=request.user,
            previous_status=previous_status,
            new_status=new_status,
            previous_start_time=reservation.start_time,
            previous_end_time=reservation.end_time,
            new_start_time=reservation.start_time,
            new_end_time=reservation.end_time,
            reason=reason
        )

        description = (
            f'{action} reservation #{reservation.pk} '
            f'for {reservation.facility.name}, '
            f'requested by {reservation.user.username}.'
        )

        if reason:
            description += f' Reason: {reason}'

        record_audit(
            request,
            action,
            reservation,
            description
        )

    return reservation


def reschedule_reservation(
    request,
    reservation_id,
    new_start,
    new_end,
    reason
):
    reason = reason.strip()

    if not reason:
        raise ValidationError(
            'A rescheduling reason is required.'
        )

    start_time = parse_datetime(new_start)
    end_time = parse_datetime(new_end)

    if start_time is None or end_time is None:
        raise ValidationError(
            'Please enter valid start and end times.'
        )

    if timezone.is_naive(start_time):
        start_time = timezone.make_aware(
            start_time,
            timezone.get_current_timezone()
        )

    if timezone.is_naive(end_time):
        end_time = timezone.make_aware(
            end_time,
            timezone.get_current_timezone()
        )

    reservation_reference = Reservation.objects.only(
        'facility_id'
    ).get(pk=reservation_id)

    with transaction.atomic():
        Facility.objects.filter(
            pk=reservation_reference.facility_id
        ).update(is_active=F('is_active'))

        reservation = (
            Reservation.objects
            .select_for_update()
            .select_related(
                'facility',
                'facility__category',
                'user'
            )
            .get(pk=reservation_id)
        )

        if reservation.status != 'approved':
            raise ValidationError(
                'Only approved reservations can be rescheduled.'
            )

        if reservation.start_time <= timezone.now():
            raise ValidationError(
                'Reservations that have already started '
                'cannot be rescheduled.'
            )

        previous_start = reservation.start_time
        previous_end = reservation.end_time

        if (
            previous_start == start_time
            and previous_end == end_time
        ):
            raise ValidationError(
                'The new schedule must be different '
                'from the existing schedule.'
            )

        reservation.start_time = start_time
        reservation.end_time = end_time

        reservation.full_clean()

        reservation.save(
            update_fields=[
                'start_time',
                'end_time'
            ]
        )

        ReservationChange.objects.create(
            reservation=reservation,
            changed_by=request.user,
            previous_status='approved',
            new_status='approved',
            previous_start_time=previous_start,
            previous_end_time=previous_end,
            new_start_time=start_time,
            new_end_time=end_time,
            reason=reason
        )

        record_audit(
            request,
            'UPDATE',
            reservation,
            (
                f'Rescheduled reservation #{reservation.pk} '
                f'for {reservation.facility.name}. '
                f'Previous: {previous_start} to {previous_end}. '
                f'New: {start_time} to {end_time}. '
                f'Reason: {reason}'
            )
        )

    return reservation