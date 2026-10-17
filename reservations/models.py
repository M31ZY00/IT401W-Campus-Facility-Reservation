from datetime import timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from facilities.models import Facility, FacilityClosure
from management.models import SystemSetting

MANILA_TIMEZONE = ZoneInfo('Asia/Manila')


class Reservation(models.Model):

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
        ('checked_in', 'Checked In'),
        ('completed', 'Completed'),
        ('no_show', 'No Show'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    facility = models.ForeignKey(
        Facility,
        on_delete=models.PROTECT
    )

    event_title = models.CharField(
        max_length=200
    )

    purpose = models.TextField()

    participant_count = models.PositiveIntegerField(
        default=1
    )

    start_time = models.DateTimeField()

    end_time = models.DateTimeField()

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    decision_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='reservation_decisions'
    )

    decision_at = models.DateTimeField(
        null=True,
        blank=True
    )

    decision_reason = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def clean(self):
        super().clean()

        errors = {}

        if not self.event_title or not self.event_title.strip():
            errors['event_title'] = (
                'Event title is required.'
            )

        if not self.start_time or not self.end_time:
            if errors:
                raise ValidationError(errors)
            return

        if self.end_time <= self.start_time:
            errors['end_time'] = (
                'End time must be later than start time.'
            )

        if not self.facility_id:
            if errors:
                raise ValidationError(errors)
            return

        facility = self.facility

        if self.status in ['pending', 'approved']:

            system_setting = SystemSetting.get_current()

            max_booking_hours = system_setting.max_booking_hours
            advance_booking_days = system_setting.advance_booking_days

            now = timezone.now()

            if self.start_time <= now:
                errors['start_time'] = (
                    'Reservation start time must be in the future.'
                )

            start_local = timezone.localtime(
                self.start_time,
                MANILA_TIMEZONE
            )

            end_local = timezone.localtime(
                self.end_time,
                MANILA_TIMEZONE
            )

            today = timezone.localtime(
                now,
                MANILA_TIMEZONE
            ).date()

            if start_local.date() != end_local.date():
                errors['end_time'] = (
                    'Reservations must start and end on the same day.'
                )

            if start_local.date() > today + timedelta(
                    days=advance_booking_days
            ):
                errors['start_time'] = (
                    f'Reservations can only be made up to '
                    f'{advance_booking_days} calendar days in advance.'
                )

            if self.end_time - self.start_time > timedelta(
                    hours=max_booking_hours
            ):
                errors['end_time'] = (
                    f'Maximum reservation duration is '
                    f'{max_booking_hours} hours.'
                )

            if (
                    start_local.time() < facility.opening_time
                    or end_local.time() > facility.closing_time
            ):
                errors['start_time'] = (
                    'Reservation must be within facility operating hours.'
                )

            if not facility.is_active:
                errors['facility'] = (
                    'This facility is currently inactive.'
                )

            if facility.category_id is None:

                errors['facility'] = (
                    'This facility does not have an assigned category.'
                )

            elif not facility.category.is_active:

                errors['facility'] = (
                    'This facility category is currently inactive.'
                )

            if not self.participant_count or self.participant_count < 1:
                errors['participant_count'] = (
                    'Participant count must be at least 1.'
                )

            elif self.participant_count > facility.capacity:
                errors['participant_count'] = (
                    f'Maximum facility capacity is {facility.capacity}.'
                )

            closure_exists = FacilityClosure.objects.filter(
                facility=facility,
                is_active=True,
                start_time__lt=self.end_time,
                end_time__gt=self.start_time
            ).exists()

            if closure_exists:
                errors['start_time'] = (
                    'This facility is unavailable due to a closure.'
                )

        if self.status == 'approved':

            conflicting_reservations = Reservation.objects.filter(
                facility=facility,
                status__in=[
                    'approved',
                    'checked_in',
                    'completed',
                    'no_show'
                ],
                start_time__lt=self.end_time,
                end_time__gt=self.start_time
            ).exclude(pk=self.pk)

            if conflicting_reservations.exists():
                errors['start_time'] = (
                    'This facility already has an approved '
                    'reservation during the selected time.'
                )

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return (
            f'Reservation #{self.pk} - '
            f'{self.facility.name} - '
            f'{self.get_status_display()}'
        )


class ReservationChange(models.Model):

    reservation = models.ForeignKey(
        Reservation,
        on_delete=models.CASCADE,
        related_name='changes'
    )

    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT
    )

    previous_status = models.CharField(
        max_length=20,
        blank=True
    )

    new_status = models.CharField(
        max_length=20
    )

    previous_start_time = models.DateTimeField(
        null=True,
        blank=True
    )

    previous_end_time = models.DateTimeField(
        null=True,
        blank=True
    )

    new_start_time = models.DateTimeField(
        null=True,
        blank=True
    )

    new_end_time = models.DateTimeField(
        null=True,
        blank=True
    )

    reason = models.TextField(
        blank=True
    )

    changed_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ['-changed_at']

    def __str__(self):
        return (
            f'Reservation #{self.reservation_id}: '
            f'{self.previous_status} → {self.new_status}'
        )


class EventRecord(models.Model):

    reservation = models.OneToOneField(
        Reservation,
        on_delete=models.CASCADE,
        related_name='event_record'
    )

    actual_start = models.DateTimeField(
        null=True,
        blank=True
    )

    actual_end = models.DateTimeField(
        null=True,
        blank=True
    )

    checked_in_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='event_check_ins'
    )

    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='completed_events'
    )

    no_show_at = models.DateTimeField(
        null=True,
        blank=True
    )

    no_show_marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='marked_no_show_events'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return (
            f'Event Record - Reservation #{self.reservation_id}'
        )


class EventIncident(models.Model):

    event_record = models.ForeignKey(
        EventRecord,
        on_delete=models.CASCADE,
        related_name='incidents'
    )

    description = models.TextField()

    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT
    )

    reported_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ['-reported_at']

    def __str__(self):
        return (
            f'Incident #{self.pk} - '
            f'Reservation #{self.event_record.reservation_id}'
        )