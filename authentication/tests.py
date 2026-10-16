from django.contrib.auth import get_user_model
from django.test import TestCase


User = get_user_model()


class AccountTests(TestCase):

    def setUp(self):

        self.basic_user = User.objects.create_user(
            username='testbasicuser',
            email='basic@example.com',
            password='TestPassword123!'
        )

        self.admin_user = User.objects.create_user(
            username='testadmin',
            email='admin@example.com',
            password='AdminPassword123!',
            is_staff=True
        )

    def test_user_password_is_hashed(self):

        self.assertNotEqual(
            self.basic_user.password,
            'TestPassword123!'
        )

        self.assertTrue(
            self.basic_user.check_password('TestPassword123!')
        )

    def test_basic_user_can_login(self):

        login_successful = self.client.login(
            username='testbasicuser',
            password='TestPassword123!'
        )

        self.assertTrue(login_successful)

    def test_admin_can_login(self):

        login_successful = self.client.login(
            username='testadmin',
            password='AdminPassword123!'
        )

        self.assertTrue(login_successful)

    def test_wrong_password_is_rejected(self):

        login_successful = self.client.login(
            username='testbasicuser',
            password='WrongPassword123!'
        )

        self.assertFalse(login_successful)

    def test_deactivated_user_cannot_login(self):

        self.basic_user.is_active = False

        self.basic_user.save(
            update_fields=['is_active']
        )

        login_successful = self.client.login(
            username='testbasicuser',
            password='TestPassword123!'
        )

        self.assertFalse(login_successful)

    def test_basic_user_is_not_admin(self):

        self.assertFalse(
            self.basic_user.is_staff
        )

        self.assertFalse(
            self.basic_user.is_superuser
        )

    def test_admin_has_staff_permission(self):

        self.assertTrue(
            self.admin_user.is_staff
        )