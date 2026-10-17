from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.urls import reverse
from django.utils import timezone

from facilities.models import (
    Facility,
    FacilityCategory,
    FacilityClosure
)
from reservations.models import Reservation

from django.contrib.auth import get_user_model
from django.test import TestCase

from management.models import SystemSetting, AuditLog

User = get_user_model()


class AdminAccessTests(TestCase):

    def setUp(self):

        self.basic_user = User.objects.create_user(
            username='basicuser',
            email='basicuser@example.com',
            password='TestPassword123!'
        )

        self.admin_user = User.objects.create_user(
            username='adminuser',
            email='adminuser@example.com',
            password='AdminPassword123!',
            is_staff=True
        )

        self.admin_pages = [
            '/manage/',
            '/manage/reservations/',
            '/manage/audit-logs/',
            '/manage/settings/'
        ]

    def test_guest_cannot_access_admin_pages(self):

        for page in self.admin_pages:

            with self.subTest(page=page):

                response = self.client.get(page)

                self.assertEqual(
                    response.status_code,
                    302
                )

    def test_basic_user_cannot_access_admin_pages(self):

        self.client.force_login(
            self.basic_user
        )

        for page in self.admin_pages:

            with self.subTest(page=page):

                response = self.client.get(page)

                self.assertEqual(
                    response.status_code,
                    403
                )

    def test_admin_can_access_admin_dashboard(self):

        self.client.force_login(
            self.admin_user
        )

        response = self.client.get(
            '/manage/'
        )

        self.assertEqual(
            response.status_code,
            200
        )


class SystemSettingTests(TestCase):

    def test_default_system_settings(self):

        system_setting = SystemSetting.get_current()

        self.assertEqual(
            system_setting.max_booking_hours,
            4
        )

        self.assertEqual(
            system_setting.advance_booking_days,
            30
        )

    def test_system_settings_can_be_updated(self):

        system_setting = SystemSetting.get_current()

        system_setting.max_booking_hours = 6

        system_setting.advance_booking_days = 60

        system_setting.save()

        updated_setting = SystemSetting.get_current()

        self.assertEqual(
            updated_setting.max_booking_hours,
            6
        )

        self.assertEqual(
            updated_setting.advance_booking_days,
            60
        )

    def test_system_settings_use_single_record(self):

        first_setting = SystemSetting.get_current()

        second_setting = SystemSetting.get_current()

        self.assertEqual(
            first_setting.pk,
            second_setting.pk
        )

        self.assertEqual(
            SystemSetting.objects.count(),
            1
        )


class ClosurePreviewTests(TestCase):

    def setUp(self):

        self.admin = User.objects.create_user(
            username='closureadmin',
            password='TestPassword123!',
            is_staff=True
        )

        self.basic_user = User.objects.create_user(
            username='closureuser',
            password='TestPassword123!'
        )

        self.category = FacilityCategory.objects.create(
            name='Closure Test Rooms',
            is_active=True
        )

        self.facility = Facility.objects.create(
            category=self.category,
            code='CLOSURE-001',
            name='Closure Test Laboratory',
            location='CICT Building',
            capacity=40,
            opening_time=time(8, 0),
            closing_time=time(17, 0),
            is_active=True
        )

        self.event_date = (
            timezone.localdate() + timedelta(days=7)
        )

        self.booking = Reservation.objects.create(
            user=self.basic_user,
            facility=self.facility,
            event_title='Programming Seminar',
            purpose='Academic programming seminar',
            participant_count=20,
            start_time=self.make_datetime(9),
            end_time=self.make_datetime(11),
            status='approved'
        )

    def make_datetime(self, hour):

        return timezone.make_aware(
            datetime.combine(
                self.event_date,
                time(hour, 0)
            ),
            ZoneInfo('Asia/Manila')
        )

    def closure_data(
        self,
        action='preview',
        start_hour=10,
        end_hour=12
    ):

        return {
            'facility': self.facility.pk,
            'start_time': self.make_datetime(
                start_hour
            ).strftime('%Y-%m-%dT%H:%M'),
            'end_time': self.make_datetime(
                end_hour
            ).strftime('%Y-%m-%dT%H:%M'),
            'reason': 'Scheduled facility maintenance',
            'action': action
        }

    def test_preview_shows_approved_conflict(self):

        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('add_closure'),
            self.closure_data()
        )

        self.assertEqual(response.status_code, 200)

        self.assertContains(
            response,
            'Conflicting Reservations'
        )

        self.assertContains(
            response,
            f'#{self.booking.pk}'
        )

        # Preview must never create a closure.
        self.assertEqual(
            FacilityClosure.objects.count(),
            0
        )

    def test_conflicting_closure_cannot_be_saved(self):

        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('add_closure'),
            self.closure_data(action='save')
        )

        self.assertEqual(response.status_code, 200)

        self.assertFalse(
            FacilityClosure.objects.exists()
        )

    def test_successful_closure_records_creator(self):

        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('add_closure'),
            self.closure_data(
                action='save',
                start_hour=13,
                end_hour=14
            )
        )

        self.assertEqual(response.status_code, 302)

        closure = FacilityClosure.objects.get()

        self.assertEqual(
            closure.created_by,
            self.admin
        )

        self.assertTrue(
            AuditLog.objects.filter(
                admin_user=self.admin,
                action='CREATE',
                model_name='FacilityClosure',
                object_id=closure.pk
            ).exists()
        )

    def test_preview_detects_existing_closure(self):

        FacilityClosure.objects.create(
            facility=self.facility,
            start_time=self.make_datetime(13),
            end_time=self.make_datetime(15),
            reason='Existing maintenance',
            is_active=True,
            created_by=self.admin
        )

        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('add_closure'),
            self.closure_data(
                start_hour=14,
                end_hour=16
            )
        )

        self.assertEqual(response.status_code, 200)

        self.assertContains(
            response,
            'Existing Active Closures'
        )

        self.assertTrue(
            response.context['preview_has_conflicts']
        )

        self.assertEqual(
            FacilityClosure.objects.count(),
            1
        )

    def test_edit_preview_excludes_current_closure(self):

        closure = FacilityClosure.objects.create(
            facility=self.facility,
            start_time=self.make_datetime(13),
            end_time=self.make_datetime(14),
            reason='Existing maintenance',
            is_active=True,
            created_by=self.admin
        )

        self.client.force_login(self.admin)

        response = self.client.post(
            reverse(
                'edit_closure',
                args=[closure.pk]
            ),
            self.closure_data(
                start_hour=13,
                end_hour=14
            )
        )

        self.assertEqual(response.status_code, 200)

        self.assertFalse(
            response.context['preview_has_conflicts']
        )

        self.assertEqual(
            FacilityClosure.objects.count(),
            1
        )

    def test_edit_keeps_original_creator(self):

        closure = FacilityClosure.objects.create(
            facility=self.facility,
            start_time=self.make_datetime(13),
            end_time=self.make_datetime(14),
            reason='Initial maintenance',
            is_active=True,
            created_by=self.admin
        )

        second_admin = User.objects.create_user(
            username='secondclosureadmin',
            password='TestPassword123!',
            is_staff=True
        )

        self.client.force_login(second_admin)

        response = self.client.post(
            reverse(
                'edit_closure',
                args=[closure.pk]
            ),
            self.closure_data(
                action='save',
                start_hour=14,
                end_hour=15
            )
        )

        self.assertEqual(response.status_code, 302)

        closure.refresh_from_db()

        self.assertEqual(
            closure.created_by,
            self.admin
        )

        self.assertTrue(
            AuditLog.objects.filter(
                admin_user=second_admin,
                action='UPDATE',
                model_name='FacilityClosure',
                object_id=closure.pk
            ).exists()
        )

    def test_basic_user_cannot_preview_closure(self):

        self.client.force_login(self.basic_user)

        response = self.client.post(
            reverse('add_closure'),
            self.closure_data()
        )

        self.assertEqual(response.status_code, 403)

        self.assertFalse(
            FacilityClosure.objects.exists()
        )
