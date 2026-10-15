from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import SystemSetting


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