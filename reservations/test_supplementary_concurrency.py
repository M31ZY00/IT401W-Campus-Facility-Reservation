import threading
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection, connections
from django.db.utils import OperationalError
from django.test import RequestFactory, TransactionTestCase
from django.utils import timezone

from facilities.models import Facility, FacilityCategory
from management.models import AuditLog, SystemSetting
from reservations.models import Reservation, ReservationChange
from reservations.services import update_reservation

MANILA = ZoneInfo('Asia/Manila')


class SupplementaryConcurrentApprovalTests(TransactionTestCase):
    """
    Supplementary Concurrency Test for CFRS
    Evaluates whether two simultaneous approval attempts for conflicting pending
    reservations on the same facility are concurrency-safe under the configured
    SQLite database backend.
    """

    def setUp(self):
        User = get_user_model()
        self.user_a = User.objects.create_user(
            username='concurrent_user_a',
            password='TestPassword123!'
        )
        self.user_b = User.objects.create_user(
            username='concurrent_user_b',
            password='TestPassword123!'
        )
        self.admin = User.objects.create_user(
            username='concurrent_admin',
            password='AdminPassword123!',
            is_staff=True
        )

        self.category = FacilityCategory.objects.create(
            name='Concurrency Test Category',
            is_active=True
        )

        self.facility = Facility.objects.create(
            category=self.category,
            code='CONC-FAC-01',
            name='Concurrency Hall',
            location='Campus Center',
            capacity=80,
            opening_time=time(8, 0),
            closing_time=time(17, 0),
            is_active=True
        )

        setting = SystemSetting.get_current()
        setting.max_booking_hours = 4
        setting.advance_booking_days = 30
        setting.save()

        self.event_date = timezone.localdate() + timedelta(days=6)
        self.factory = RequestFactory()

    def make_aware_dt(self, hour, minute=0):
        return timezone.make_aware(
            datetime.combine(self.event_date, time(hour, minute)),
            MANILA
        )

    def test_concurrent_conflicting_approvals(self):
        """
        Execute two concurrent approval attempts for overlapping reservations
        competing for the same facility.

        Required assertions:
        1. Exactly one conflicting reservation becomes Approved.
        2. The other reservation is not approved and is handled according to intended failure behavior.
        3. The losing request does not produce an unhandled server error or database-lock error.
        4. No partially updated reservation, incorrect state transition, or inconsistent audit record.
        5. The final database state contains no pair of overlapping Approved reservations.
        """
        # Create two overlapping Pending reservations on the same facility
        # Res A: 10:00 - 12:00
        # Res B: 11:00 - 13:00 (1 hour overlap)
        res_a = Reservation.objects.create(
            user=self.user_a,
            facility=self.facility,
            event_title='Competing Event Alpha',
            purpose='Concurrent approval competition A',
            participant_count=30,
            start_time=self.make_aware_dt(10, 0),
            end_time=self.make_aware_dt(12, 0),
            status='pending'
        )

        res_b = Reservation.objects.create(
            user=self.user_b,
            facility=self.facility,
            event_title='Competing Event Beta',
            purpose='Concurrent approval competition B',
            participant_count=35,
            start_time=self.make_aware_dt(11, 0),
            end_time=self.make_aware_dt(13, 0),
            status='pending'
        )

        barrier = threading.Barrier(2)
        results = {}

        def approve_worker(key, res_id):
            # Close existing connection to ensure independent thread connection
            connections.close_all()
            req = self.factory.post('/manage/reservations/update-status/')
            req.user = self.admin

            try:
                # Synchronize start of both workers
                barrier.wait(timeout=5)
                res = update_reservation(req, res_id, 'APPROVE', f'Approved in thread {key}')
                results[key] = ('SUCCESS', res.status, None)
            except ValidationError as ve:
                results[key] = ('VALIDATION_ERROR', 'pending', ve)
            except OperationalError as oe:
                results[key] = ('DATABASE_LOCKED', 'locked', oe)
            except Exception as e:
                results[key] = ('UNEXPECTED_ERROR', type(e).__name__, e)
            finally:
                connections.close_all()

        t1 = threading.Thread(target=approve_worker, args=('A', res_a.pk))
        t2 = threading.Thread(target=approve_worker, args=('B', res_b.pk))

        t1.start()
        t2.start()

        t1.join(timeout=10)
        t2.join(timeout=10)

        # Refresh database state
        res_a.refresh_from_db()
        res_b.refresh_from_db()

        outcome_types = [results.get('A', (None,))[0], results.get('B', (None,))[0]]

        # Log observed outcome for diagnostic evidence
        print(f"\n[CONCURRENCY TEST OUTCOME] Worker A: {results.get('A')}, Worker B: {results.get('B')}")
        print(f"[CONCURRENCY TEST STATE] Res A status: {res_a.status}, Res B status: {res_b.status}")

        # Each check runs inside its own subTest, so a failed check is reported
        # but the remaining checks still run.

        # Assertion 1: Exactly one conflicting reservation becomes Approved
        with self.subTest('1. Exactly one reservation is approved'):
            approved_reservations = Reservation.objects.filter(
                facility=self.facility,
                status='approved',
                pk__in=[res_a.pk, res_b.pk]
            )
            self.assertEqual(
                approved_reservations.count(),
                1,
                f"Expected exactly 1 approved reservation, found {approved_reservations.count()}."
            )

        # Assertion 2: The other reservation is not approved
        with self.subTest('2. The other reservation stays pending'):
            non_approved = Reservation.objects.filter(
                facility=self.facility,
                status='pending',
                pk__in=[res_a.pk, res_b.pk]
            )
            self.assertEqual(
                non_approved.count(),
                1,
                "The competing reservation should remain pending upon conflict rejection."
            )

        # Assertion 3: The losing request does not produce an unhandled database-lock error
        # A database-lock exception must not be counted as a successful conflict rejection
        with self.subTest('3. No database lock error or unexpected error'):
            self.assertNotIn(
                'DATABASE_LOCKED',
                outcome_types,
                f"Concurrency safety failed: database lock error occurred during contention: {results}"
            )
            self.assertNotIn(
                'UNEXPECTED_ERROR',
                outcome_types,
                f"Unhandled exception during concurrent approval: {results}"
            )

        # Assertion 4: No partially updated reservation, incorrect state transition, or inconsistent audit record
        with self.subTest('4. No partial update or inconsistent audit record'):
            losing_key = 'A' if results.get('A', (None,))[0] != 'SUCCESS' else 'B'
            losing_res = res_a if losing_key == 'A' else res_b

            # Losing reservation must not have status change records
            losing_changes = ReservationChange.objects.filter(reservation=losing_res)
            self.assertEqual(
                losing_changes.count(),
                0,
                "Losing reservation must have no committed ReservationChange records."
            )

            # AuditLog for losing reservation should not record APPROVE
            losing_audits = AuditLog.objects.filter(
                model_name='Reservation',
                object_id=losing_res.pk,
                action='APPROVE'
            )
            self.assertEqual(
                losing_audits.count(),
                0,
                "Losing reservation must not have an APPROVE AuditLog."
            )

        # Assertion 5: The final database state contains no pair of overlapping Approved reservations
        with self.subTest('5. No overlapping approved reservations'):
            approved_all = list(Reservation.objects.filter(facility=self.facility, status='approved'))
            for i in range(len(approved_all)):
                for j in range(i + 1, len(approved_all)):
                    r1 = approved_all[i]
                    r2 = approved_all[j]
                    overlap = (r1.start_time < r2.end_time) and (r1.end_time > r2.start_time)
                    self.assertFalse(
                        overlap,
                        f"Final database state contains overlapping approved reservations: #{r1.pk} and #{r2.pk}"
                    )