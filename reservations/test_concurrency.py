import sqlite3
import threading
from datetime import datetime, time, timedelta
from unittest import skipUnless
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.db import OperationalError, connection
from django.test import Client, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from facilities.models import Facility, FacilityCategory
from management.models import SystemSetting
from reservations.models import Reservation

MANILA = ZoneInfo('Asia/Manila')
ROUNDS = 10

USES_FILE_DATABASE = bool(connection.settings_dict['TEST'].get('NAME'))


def run_together(actions):
    barrier = threading.Barrier(len(actions))
    results = [None] * len(actions)

    def worker(index, action):
        try:
            barrier.wait(timeout=30)
            results[index] = ('ok', action())
        except Exception as error:
            results[index] = ('error', repr(error))
        finally:
            connection.close()

    threads = [
        threading.Thread(target=worker, args=(index, action))
        for index, action in enumerate(actions)
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    return results


@skipUnless(
    USES_FILE_DATABASE,
    'Run with --settings=config.settings_concurrency (needs a database file).'
)
class ConcurrencyTestBase(TransactionTestCase):

    def setUp(self):
        User = get_user_model()

        admins = [
            User.objects.create_user(
                username=f'race_admin_{number}',
                password='TestPassword123!',
                is_staff=True
            )
            for number in range(2)
        ]

        users = [
            User.objects.create_user(
                username=f'race_user_{number}',
                password='TestPassword123!'
            )
            for number in range(8)
        ]

        category = FacilityCategory.objects.create(
            name='Race Rooms',
            is_active=True
        )

        self.facility = Facility.objects.create(
            category=category,
            code='RACE-001',
            name='Race Room',
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

        self.users = users
        self.admin_clients = [self.client_for(admin) for admin in admins]
        self.user_clients = [self.client_for(user) for user in users]

    def client_for(self, user):
        client = Client()
        client.force_login(user)
        return client

    def at(self, day, hour):
        date = timezone.localdate() + timedelta(days=day)

        return timezone.make_aware(
            datetime.combine(date, time(hour, 0)),
            MANILA
        )

    def pending(self, user, day, start_hour, end_hour):
        return Reservation.objects.create(
            user=user,
            facility=self.facility,
            event_title='Race booking',
            purpose='Concurrency check',
            participant_count=10,
            start_time=self.at(day, start_hour),
            end_time=self.at(day, end_hour),
            status='pending'
        )

    def approve(self, client, reservation):
        def action():
            response = client.post(
                reverse('update_reservation_status', args=[reservation.pk]),
                {'action': 'approve', 'reason': 'Concurrency check'}
            )

            return [
                str(message)
                for message in get_messages(response.wsgi_request)
            ]

        return action

    def book(self, client, day, hour):
        def action():
            response = client.post(
                reverse('create_reservation', args=[self.facility.pk]),
                {
                    'event_title': 'Race booking',
                    'purpose': 'Concurrency check',
                    'participant_count': 10,
                    'start_time': self.at(day, hour).strftime('%Y-%m-%dT%H:%M'),
                    'end_time': self.at(day, hour + 1).strftime('%Y-%m-%dT%H:%M'),
                }
            )

            return response.status_code

        return action

    def approval_race(self, day):
        first = self.pending(self.users[0], day, 9, 11)
        second = self.pending(self.users[1], day, 10, 12)

        return [
            self.approve(self.admin_clients[0], first),
            self.approve(self.admin_clients[1], second),
        ]

    def approved_count(self, day):
        return Reservation.objects.filter(
            facility=self.facility,
            status='approved',
            start_time__gte=self.at(day, 0),
            start_time__lt=self.at(day + 1, 0)
        ).count()

    def lock_problems(self, results):
        problems = []

        for kind, value in results:
            if kind == 'error':
                problems.append(value)
            elif isinstance(value, list) and any(
                'database conflict' in message for message in value
            ):
                problems.append(value)

        return problems


class SimultaneousApprovalTests(ConcurrencyTestBase):

    def test_overlapping_reservations_are_never_both_approved(self):
        for day in range(1, ROUNDS + 1):
            with self.subTest(day=day):
                run_together(self.approval_race(day))
                self.assertLessEqual(self.approved_count(day), 1)

    def test_simultaneous_approvals_do_not_hit_a_database_lock(self):
        for day in range(1, ROUNDS + 1):
            with self.subTest(day=day):
                results = run_together(self.approval_race(day))
                self.assertEqual(self.lock_problems(results), [])
                self.assertEqual(self.approved_count(day), 1)


class SimultaneousBookingTests(ConcurrencyTestBase):

    def test_eight_users_can_book_at_the_same_moment(self):
        results = run_together([
            self.book(client, 3, 8 + number)
            for number, client in enumerate(self.user_clients)
        ])

        self.assertEqual(self.lock_problems(results), [])
        self.assertEqual([value for kind, value in results], [302] * 8)
        self.assertEqual(Reservation.objects.count(), 8)

    def test_bookings_and_approvals_at_the_same_moment(self):
        actions = self.approval_race(1) + [
            self.book(client, 3, 8 + number)
            for number, client in enumerate(self.user_clients[2:])
        ]

        results = run_together(actions)

        self.assertEqual(self.lock_problems(results), [])
        self.assertEqual(self.approved_count(1), 1)
        self.assertEqual(Reservation.objects.count(), 8)

    def test_thirty_users_can_book_at_the_same_moment(self):
        User = get_user_model()

        clients = [
            self.client_for(
                User.objects.create_user(
                    username=f'crowd_user_{number}',
                    password='TestPassword123!'
                )
            )
            for number in range(30)
        ]

        results = run_together([
            self.book(client, 3, 8 + number % 8)
            for number, client in enumerate(clients)
        ])

        self.assertEqual(self.lock_problems(results), [])
        self.assertEqual([value for kind, value in results], [302] * 30)
        self.assertEqual(Reservation.objects.count(), 30)


class LockedDatabaseTests(ConcurrencyTestBase):

    def hold_lock(self):
        locker = sqlite3.connect(
            connection.settings_dict['NAME'],
            isolation_level=None
        )

        locker.execute('BEGIN IMMEDIATE')

        return locker

    def release_lock(self, locker):
        locker.execute('ROLLBACK')
        locker.close()

    def test_booking_while_the_database_is_locked(self):
        locker = self.hold_lock()

        try:
            with self.assertRaises(OperationalError):
                self.book(self.user_clients[0], 3, 9)()
        finally:
            self.release_lock(locker)

        self.assertEqual(Reservation.objects.count(), 0)

    def test_approval_while_the_database_is_locked(self):
        reservation = self.pending(self.users[0], 1, 9, 11)

        locker = self.hold_lock()

        try:
            messages = self.approve(self.admin_clients[0], reservation)()
        finally:
            self.release_lock(locker)

        self.assertTrue(
            any('database conflict' in message for message in messages)
        )

        reservation.refresh_from_db()
        self.assertEqual(reservation.status, 'pending')