from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from facilities.models import Facility, FacilityCategory
from reservations.forms import ReservationForm
from reservations.models import Reservation


class RequiredFieldValidationTests(TestCase):

    def setUp(self):

        self.category = FacilityCategory.objects.create(
            name='Computer Laboratories',
            is_active=True
        )

        self.facility = Facility.objects.create(
            category=self.category,
            code='TEST-SDL-001',
            name='Test SDL 1',
            location='CICT Building',
            capacity=40,
            opening_time=time(8, 0),
            closing_time=time(17, 0),
            is_active=True
        )

        self.user = get_user_model().objects.create_user(
            username='validationuser',
            password='TestPassword123!'
        )

        event_date = (
            timezone.localdate() + timedelta(days=5)
        )

        self.start_time = timezone.make_aware(
            datetime.combine(event_date, time(9, 0)),
            ZoneInfo('Asia/Manila')
        )

        self.end_time = self.start_time + timedelta(
            hours=1
        )

    def make_reservation(self, title):

        return Reservation(
            user=self.user,
            facility=self.facility,
            event_title=title,
            purpose='Testing model validation',
            participant_count=20,
            start_time=self.start_time,
            end_time=self.end_time,
            status='pending'
        )

    def test_missing_facility_code_is_rejected(self):

        self.facility.code = ''

        with self.assertRaises(ValidationError) as result:
            self.facility.full_clean()

        self.assertIn(
            'code',
            result.exception.message_dict
        )

    def test_missing_category_is_rejected(self):

        self.facility.category = None

        with self.assertRaises(ValidationError) as result:
            self.facility.full_clean()

        self.assertIn(
            'category',
            result.exception.message_dict
        )

    def test_zero_capacity_is_rejected(self):

        self.facility.capacity = 0

        with self.assertRaises(ValidationError) as result:
            self.facility.full_clean()

        self.assertIn(
            'capacity',
            result.exception.message_dict
        )

    def test_invalid_operating_hours_are_rejected(self):

        self.facility.opening_time = time(17, 0)
        self.facility.closing_time = time(8, 0)

        with self.assertRaises(ValidationError) as result:
            self.facility.full_clean()

        self.assertIn(
            'closing_time',
            result.exception.message_dict
        )

    def test_blank_event_title_is_rejected(self):

        reservation = self.make_reservation('')

        with self.assertRaises(ValidationError) as result:
            reservation.full_clean()

        self.assertIn(
            'event_title',
            result.exception.message_dict
        )

    def test_whitespace_event_title_is_rejected(self):

        reservation = self.make_reservation('   ')

        with self.assertRaises(ValidationError) as result:
            reservation.full_clean()

        self.assertIn(
            'event_title',
            result.exception.message_dict
        )

    def test_valid_reservation_passes_validation(self):

        reservation = self.make_reservation(
            'Software Development Workshop'
        )

        reservation.full_clean()

        self.assertEqual(
            reservation.event_title,
            'Software Development Workshop'
        )

    def test_reservation_form_requires_event_title(self):

        form = ReservationForm(
            data={
                'event_title': '',
                'purpose': 'Testing form validation',
                'participant_count': 20,
                'start_time': self.start_time.strftime(
                    '%Y-%m-%dT%H:%M'
                ),
                'end_time': self.end_time.strftime(
                    '%Y-%m-%dT%H:%M'
                ),
            }
        )

        self.assertFalse(form.is_valid())

        self.assertIn(
            'event_title',
            form.errors
        )
