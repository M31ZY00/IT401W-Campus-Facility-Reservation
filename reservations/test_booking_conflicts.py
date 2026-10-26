from datetime import datetime, time, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import OperationalError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from facilities.models import Facility, FacilityCategory
from management.models import AuditLog, SystemSetting
from reservations.models import Reservation, ReservationChange

MANILA = ZoneInfo('Asia/Manila')


class BookingTestBase(TestCase):

    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(
            username='conflictuser',
            password='TestPassword123!'
        )

        self.other_user = User.objects.create_user(
            username='conflictother',
            password='TestPassword123!'
        )

        category = FacilityCategory.objects.create(
            name='Conflict Test Rooms',
            is_active=True
        )

        self.facility = Facility.objects.create(
            category=category,
            code='CONFLICT-001',
            name='Conflict Room 1',
            location='Main Building',
            capacity=50,
            opening_time=time(8, 0),
            closing_time=time(17, 0),
            is_active=True
        )

        self.other_facility = Facility.objects.create(
            category=category,
            code='CONFLICT-002',
            name='Conflict Room 2',
            location='Main Building',
            capacity=50,
            opening_time=time(8, 0),
            closing_time=time(17, 0),
            is_active=True
        )

        setting = SystemSetting.get_current()
        setting.max_booking_hours = 4
        setting.advance_booking_days = 30
        setting.save()

        self.event_date = timezone.localdate() + timedelta(days=5)

    def at(self, hour, minute=0):
        return timezone.make_aware(
            datetime.combine(self.event_date, time(hour, minute)),
            MANILA
        )

    def book(self, start, end, status='approved', facility=None, user=None):
        return Reservation.objects.create(
            user=user or self.user,
            facility=facility or self.facility,
            event_title='Conflict Test Event',
            purpose='Testing booking conflicts',
            participant_count=20,
            start_time=start,
            end_time=end,
            status=status
        )

    def assert_conflict(self, reservation):
        with self.assertRaises(ValidationError) as result:
            reservation.full_clean()

        messages = result.exception.message_dict.get('start_time', [])

        self.assertTrue(
            any('already has an approved' in m for m in messages)
        )


class BookingConflictTests(BookingTestBase):

    def test_exact_same_slot_is_blocked(self):
        self.book(self.at(9), self.at(11))
        self.assert_conflict(self.book(self.at(9), self.at(11)))

    def test_overlap_at_start_is_blocked(self):
        self.book(self.at(9), self.at(11))
        self.assert_conflict(self.book(self.at(8), self.at(10)))

    def test_overlap_at_end_is_blocked(self):
        self.book(self.at(9), self.at(11))
        self.assert_conflict(self.book(self.at(10), self.at(12)))

    def test_booking_that_contains_existing_is_blocked(self):
        self.book(self.at(10), self.at(11))
        self.assert_conflict(self.book(self.at(9), self.at(12)))

    def test_booking_inside_existing_is_blocked(self):
        self.book(self.at(9), self.at(12))
        self.assert_conflict(self.book(self.at(10), self.at(11)))

    def test_adjacent_booking_before_existing_is_allowed(self):
        self.book(self.at(11), self.at(13))
        self.book(self.at(9), self.at(11)).full_clean()

    def test_same_time_on_different_facility_is_allowed(self):
        self.book(self.at(9), self.at(11))
        self.book(
            self.at(9),
            self.at(11),
            facility=self.other_facility
        ).full_clean()

    def test_rejected_booking_does_not_block_slot(self):
        self.book(self.at(9), self.at(11), status='rejected')
        self.book(self.at(9), self.at(11)).full_clean()

    def test_cancelled_booking_does_not_block_slot(self):
        self.book(self.at(9), self.at(11), status='cancelled')
        self.book(self.at(9), self.at(11)).full_clean()

    def test_in_progress_and_finished_bookings_still_block_slot(self):
        for status in ['checked_in', 'completed', 'no_show']:
            with self.subTest(status=status):
                Reservation.objects.all().delete()
                self.book(self.at(9), self.at(11), status=status)
                self.assert_conflict(self.book(self.at(10), self.at(12)))

    def test_approved_booking_does_not_conflict_with_itself(self):
        self.book(self.at(9), self.at(11)).full_clean()


class BookingCancellationTests(BookingTestBase):

    def cancel(self, reservation, user=None):
        self.client.force_login(user or self.user)

        return self.client.post(
            reverse('cancel_reservation', args=[reservation.pk])
        )

    def test_owner_can_cancel_approved_reservation(self):
        reservation = self.book(self.at(9), self.at(11))

        response = self.cancel(reservation)

        self.assertEqual(response.status_code, 302)

        reservation.refresh_from_db()
        self.assertEqual(reservation.status, 'cancelled')

        self.assertTrue(
            ReservationChange.objects.filter(
                reservation=reservation,
                previous_status='approved',
                new_status='cancelled',
                changed_by=self.user
            ).exists()
        )

        self.assertTrue(
            AuditLog.objects.filter(
                admin_user=self.user,
                action='CANCEL',
                model_name='Reservation',
                object_id=reservation.pk
            ).exists()
        )

    def test_cancelled_slot_can_be_rebooked(self):
        reservation = self.book(self.at(9), self.at(11))

        self.cancel(reservation)

        self.book(
            self.at(9),
            self.at(11),
            user=self.other_user
        ).full_clean()

    def test_cancellation_after_start_is_blocked(self):
        now = timezone.now()

        reservation = self.book(
            now - timedelta(minutes=30),
            now + timedelta(minutes=30)
        )

        self.cancel(reservation)

        reservation.refresh_from_db()
        self.assertEqual(reservation.status, 'approved')

        self.assertFalse(
            AuditLog.objects.filter(action='CANCEL').exists()
        )

    def test_other_user_cannot_cancel_reservation(self):
        reservation = self.book(self.at(9), self.at(11))

        response = self.cancel(reservation, user=self.other_user)

        self.assertEqual(response.status_code, 404)

        reservation.refresh_from_db()
        self.assertEqual(reservation.status, 'approved')

    def test_already_cancelled_reservation_cannot_be_cancelled_again(self):
        reservation = self.book(
            self.at(9),
            self.at(11),
            status='cancelled'
        )

        self.cancel(reservation)

        self.assertEqual(ReservationChange.objects.count(), 0)

        self.assertFalse(
            AuditLog.objects.filter(action='CANCEL').exists()
        )

    def test_cancel_endpoint_rejects_get_requests(self):
        reservation = self.book(self.at(9), self.at(11))

        self.client.force_login(self.user)

        response = self.client.get(
            reverse('cancel_reservation', args=[reservation.pk])
        )

        self.assertEqual(response.status_code, 405)

        reservation.refresh_from_db()
        self.assertEqual(reservation.status, 'approved')


class BookingDatabaseErrorTests(BookingTestBase):

    def test_database_error_shows_message_and_saves_nothing(self):
        self.client.force_login(self.user)

        data = {
            'event_title': 'Database error check',
            'purpose': 'Checking the error message',
            'participant_count': 10,
            'start_time': self.at(9).strftime('%Y-%m-%dT%H:%M'),
            'end_time': self.at(10).strftime('%Y-%m-%dT%H:%M'),
        }

        with patch.object(
            Reservation,
            'save',
            side_effect=OperationalError('database is locked')
        ):
            response = self.client.post(
                reverse('create_reservation', args=[self.facility.pk]),
                data
            )

        self.assertEqual(response.status_code, 200)

        self.assertIn(
            'database conflict',
            ' '.join(response.context['form'].non_field_errors())
        )

        self.assertEqual(Reservation.objects.count(), 0)
        self.assertEqual(ReservationChange.objects.count(), 0)
        self.assertEqual(AuditLog.objects.count(), 0)