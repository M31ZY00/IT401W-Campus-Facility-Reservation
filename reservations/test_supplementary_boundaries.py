from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import RequestFactory, TestCase
from django.utils import timezone

from facilities.models import Facility, FacilityCategory
from management.models import SystemSetting
from reservations.models import Reservation
from reservations.services import update_reservation

MANILA = ZoneInfo('Asia/Manila')


class SupplementaryBoundaryValueTests(TestCase):
    

    def setUp(self):
        User = get_user_model()
        self.basic_user = User.objects.create_user(
            username='bv_user_alpha',
            password='TestPassword123!'
        )
        self.other_user = User.objects.create_user(
            username='bv_user_beta',
            password='TestPassword123!'
        )
        self.admin_user = User.objects.create_user(
            username='bv_admin',
            password='AdminPassword123!',
            is_staff=True
        )

        self.category = FacilityCategory.objects.create(
            name='Boundary Test Category',
            is_active=True
        )

        self.facility = Facility.objects.create(
            category=self.category,
            code='BV-FAC-01',
            name='Boundary Test Hall',
            location='Main Campus Building A',
            capacity=60,
            opening_time=time(8, 0),
            closing_time=time(17, 0),
            is_active=True
        )

        self.system_setting = SystemSetting.get_current()
        self.system_setting.max_booking_hours = 4
        self.system_setting.advance_booking_days = 30
        self.system_setting.save()

        # Valid future local date
        self.event_date = timezone.localdate() + timedelta(days=7)
        self.factory = RequestFactory()

    def make_aware_dt(self, hour, minute=0, second=0):
        return timezone.make_aware(
            datetime.combine(self.event_date, time(hour, minute, second)),
            MANILA
        )

    def create_reservation(self, start, end, participant_count=20, status='pending', user=None):
        return Reservation(
            user=user or self.basic_user,
            facility=self.facility,
            event_title='Boundary Test Event',
            purpose='Verification of boundary conditions',
            participant_count=participant_count,
            start_time=start,
            end_time=end,
            status=status
        )

    def test_bv01_duration_equals_configured_maximum(self):
        """BV-01: Reservation duration equals the configured maximum -> Accepted"""
        max_hours = SystemSetting.get_current().max_booking_hours
        start = self.make_aware_dt(9, 0)
        end = start + timedelta(hours=max_hours)

        reservation = self.create_reservation(start, end, status='pending')
        reservation.full_clean()
        reservation.save()

        reservation.refresh_from_db()
        self.assertIsNotNone(reservation.pk)
        self.assertEqual(reservation.end_time - reservation.start_time, timedelta(hours=max_hours))
        self.assertEqual(reservation.status, 'pending')

    def test_bv02_duration_exceeds_maximum_by_one_minute(self):
        """BV-02: Duration exceeds the maximum by one minute -> Rejected"""
        max_hours = SystemSetting.get_current().max_booking_hours
        start = self.make_aware_dt(9, 0)
        end = start + timedelta(hours=max_hours, minutes=1)

        reservation = self.create_reservation(start, end, status='pending')

        with self.assertRaises(ValidationError) as ctx:
            reservation.full_clean()

        self.assertIn('end_time', ctx.exception.message_dict)
        error_messages = ctx.exception.message_dict['end_time']
        self.assertTrue(any(f'Maximum reservation duration is {max_hours} hours.' in msg for msg in error_messages))
        self.assertIsNone(reservation.pk)

    def test_bv03_participant_count_equals_facility_capacity(self):
        """BV-03: Participant count equals facility capacity -> Accepted"""
        capacity = self.facility.capacity
        start = self.make_aware_dt(9, 0)
        end = self.make_aware_dt(11, 0)

        reservation = self.create_reservation(start, end, participant_count=capacity, status='pending')
        reservation.full_clean()
        reservation.save()

        reservation.refresh_from_db()
        self.assertIsNotNone(reservation.pk)
        self.assertEqual(reservation.participant_count, capacity)

    def test_bv04_participant_count_exceeds_capacity_by_one(self):
        """BV-04: Participant count exceeds capacity by one -> Rejected"""
        capacity = self.facility.capacity
        start = self.make_aware_dt(9, 0)
        end = self.make_aware_dt(11, 0)

        reservation = self.create_reservation(start, end, participant_count=capacity + 1, status='pending')

        with self.assertRaises(ValidationError) as ctx:
            reservation.full_clean()

        self.assertIn('participant_count', ctx.exception.message_dict)
        error_messages = ctx.exception.message_dict['participant_count']
        self.assertTrue(any(f'Maximum facility capacity is {capacity}.' in msg for msg in error_messages))
        self.assertIsNone(reservation.pk)

    def test_bv05_reservation_starts_exactly_at_opening_time(self):
        """BV-05: Reservation starts exactly at opening time -> Accepted (future start)"""
        opening = self.facility.opening_time
        start = self.make_aware_dt(opening.hour, opening.minute)
        end = start + timedelta(hours=2)

        reservation = self.create_reservation(start, end, status='pending')
        reservation.full_clean()
        reservation.save()

        reservation.refresh_from_db()
        start_local = timezone.localtime(reservation.start_time, MANILA)
        self.assertEqual(start_local.time(), opening)
        self.assertGreater(reservation.start_time, timezone.now())
        self.assertEqual(reservation.status, 'pending')

    def test_bv06_reservation_ends_exactly_at_closing_time(self):
        """BV-06: Reservation ends exactly at closing time -> Accepted"""
        closing = self.facility.closing_time
        end = self.make_aware_dt(closing.hour, closing.minute)
        start = end - timedelta(hours=2)

        reservation = self.create_reservation(start, end, status='pending')
        reservation.full_clean()
        reservation.save()

        reservation.refresh_from_db()
        end_local = timezone.localtime(reservation.end_time, MANILA)
        self.assertEqual(end_local.time(), closing)
        self.assertEqual(reservation.status, 'pending')

    def test_bv07_reservation_starts_before_opening_time(self):
        """BV-07: Reservation starts before opening time -> Rejected"""
        opening = self.facility.opening_time
        start = self.make_aware_dt(opening.hour, opening.minute) - timedelta(minutes=1)
        end = start + timedelta(hours=2)

        reservation = self.create_reservation(start, end, status='pending')

        with self.assertRaises(ValidationError) as ctx:
            reservation.full_clean()

        self.assertIn('start_time', ctx.exception.message_dict)
        error_messages = ctx.exception.message_dict['start_time']
        self.assertTrue(any('operating hours' in msg for msg in error_messages))
        self.assertIsNone(reservation.pk)

    def test_bv08_reservation_ends_after_closing_time(self):
        """BV-08: Reservation ends after closing time -> Rejected"""
        closing = self.facility.closing_time
        end = self.make_aware_dt(closing.hour, closing.minute) + timedelta(minutes=1)
        start = end - timedelta(hours=2)

        reservation = self.create_reservation(start, end, status='pending')

        with self.assertRaises(ValidationError) as ctx:
            reservation.full_clean()

        self.assertIn('start_time', ctx.exception.message_dict)
        error_messages = ctx.exception.message_dict['start_time']
        self.assertTrue(any('operating hours' in msg for msg in error_messages))
        self.assertIsNone(reservation.pk)

    def test_bv09_overlapping_reservations_conflicting_approval_rejected(self):
        """BV-09: Two reservations overlap by a positive amount of time -> Conflicting approval must be rejected"""
        start1 = self.make_aware_dt(9, 0)
        end1 = self.make_aware_dt(10, 0)

        # Approved first reservation
        res1 = self.create_reservation(start1, end1, status='approved', user=self.basic_user)
        res1.full_clean()
        res1.save()

        # Conflicting second reservation overlapping by 1 minute (09:59 - 10:59)
        start2 = self.make_aware_dt(9, 59)
        end2 = self.make_aware_dt(10, 59)

        res2 = self.create_reservation(start2, end2, status='pending', user=self.other_user)
        res2.full_clean()
        res2.save()

        # Direct model-level approval check
        res2.status = 'approved'
        with self.assertRaises(ValidationError) as ctx:
            res2.full_clean()

        self.assertIn('start_time', ctx.exception.message_dict)
        self.assertTrue(any('already has an approved reservation' in msg for msg in ctx.exception.message_dict['start_time']))

        # Service-level approval check
        request = self.factory.post('/manage/reservations/update-status/')
        request.user = self.admin_user

        with self.assertRaises(ValidationError) as service_ctx:
            update_reservation(request, res2.pk, 'APPROVE', 'Attempting approval of conflicting reservation')

        self.assertTrue(any('already has an approved reservation' in str(service_ctx.exception) for _ in [1]))

        res2.refresh_from_db()
        self.assertEqual(res2.status, 'pending')

