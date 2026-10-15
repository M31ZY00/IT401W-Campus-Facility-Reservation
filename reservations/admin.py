from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Reservation


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):

    list_display = (
        'user',
        'facility',
        'start_time',
        'end_time',
        'status',
    )

    list_filter = ('status', 'facility')

    search_fields = (
        'user__username',
        'facility__name',
    )

    readonly_fields = (
        'created_at',
        'status',
    )

    actions = ['approve_reservations',
               'reject_reservations',
               'cancel_reservations',
               'check_in_reservations',
               'complete_reservations',
               'mark_no_show'
               ]

    @admin.action(description='Approve selected reservations')
    def approve_reservations(self, request, queryset):

        for reservation in queryset:

            if reservation.status != 'pending':
                self.message_user(
                    request,
                    f'Reservation #{reservation.pk} is not pending.',
                    level=messages.WARNING
                )
                continue

            reservation.status = 'approved'

            try:
                reservation.full_clean()
                reservation.save()

                self.message_user(
                    request,
                    f'Reservation #{reservation.pk} approved successfully.',
                    level=messages.SUCCESS
                )

            except ValidationError as error:
                self.message_user(
                    request,
                    f'Reservation #{reservation.pk}: {error}',
                    level=messages.ERROR
                )


    @admin.action(description='Reject selected reservations')
    def reject_reservations(self, request, queryset):

        for reservation in queryset:

            if reservation.status != 'pending':
                self.message_user(
                    request,
                    f'Reservation #{reservation.pk} cannot be rejected because it is not pending.',
                    level=messages.WARNING
                )
                continue

            reservation.status = 'rejected'
            reservation.save(update_fields=['status'])

            self.message_user(
                request,
                f'Reservation #{reservation.pk} rejected successfully.',
                level=messages.SUCCESS
            )


    @admin.action(description='Cancel selected reservations')
    def cancel_reservations(self, request, queryset):

        for reservation in queryset:

            if reservation.status not in ['pending', 'approved']:
                self.message_user(
                    request,
                    f'Reservation #{reservation.pk} cannot be cancelled '
                    f'because its status is {reservation.status}.',
                    level=messages.WARNING
                )
                continue

            reservation.status = 'cancelled'
            reservation.save(update_fields=['status'])

            self.message_user(
                request,
                f'Reservation #{reservation.pk} cancelled successfully.',
                level=messages.SUCCESS
            )


    @admin.action(description='Check in selected reservations')
    def check_in_reservations(self, request, queryset):

        for reservation in queryset:

            if reservation.status != 'approved':
                self.message_user(
                    request,
                    f'Reservation #{reservation.pk} cannot be checked in '
                    f'because it is not approved.',
                    level=messages.WARNING
                )
                continue

            reservation.status = 'checked_in'

            try:
                reservation.full_clean()
                reservation.save(update_fields=['status'])

                self.message_user(
                    request,
                    f'Reservation #{reservation.pk} checked in successfully.',
                    level=messages.SUCCESS
                )

            except ValidationError as error:
                self.message_user(
                    request,
                    f'Reservation #{reservation.pk}: {error}',
                    level=messages.ERROR
                )


    @admin.action(description='Complete selected reservations')
    def complete_reservations(self, request, queryset):

        for reservation in queryset:

            if reservation.status != 'checked_in':
                self.message_user(
                    request,
                    f'Reservation #{reservation.pk} cannot be completed '
                    f'because its status is {reservation.status}.',
                    level=messages.WARNING
                )
                continue

            reservation.status = 'completed'
            reservation.save(update_fields=['status'])

            self.message_user(
                request,
                f'Reservation #{reservation.pk} completed successfully.',
                level=messages.SUCCESS
            )

    @admin.action(description='Mark selected reservations as No Show')
    def mark_no_show(self, request, queryset):

        for reservation in queryset:

            # Only approved reservations can be marked No Show
            if reservation.status != 'approved':
                self.message_user(
                    request,
                    f'Reservation #{reservation.pk} cannot be marked No Show '
                    f'because its status is {reservation.status}.',
                    level=messages.WARNING
                )
                continue

            # Prevent marking No Show before the reservation starts
            if reservation.start_time > timezone.now():
                self.message_user(
                    request,
                    f'Reservation #{reservation.pk} cannot be marked No Show '
                    f'because its scheduled start time has not passed.',
                    level=messages.WARNING
                )
                continue

            reservation.status = 'no_show'
            reservation.save(update_fields=['status'])

            self.message_user(
                request,
                f'Reservation #{reservation.pk} marked as No Show successfully.',
                level=messages.SUCCESS
            )