from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import timezone

from facilities.models import FacilityClosure
from management.models import AuditLog
from reservations.models import ReservationChange
from reservations.test_booking_conflicts import BookingTestBase


class AdminBookingTestBase(BookingTestBase):

    def setUp(self):
        super().setUp()

        self.admin = get_user_model().objects.create_user(
            username='conflictadmin',
            password='AdminPassword123!',
            is_staff=True
        )

    def decide(self, reservation, action, reason='Test reason'):
        self.client.force_login(self.admin)

        return self.client.post(
            reverse('update_reservation_status', args=[reservation.pk]),
            {'action': action, 'reason': reason}
        )

    def reschedule(self, reservation, start, end, reason='Test reason'):
        self.client.force_login(self.admin)

        fmt = '%Y-%m-%dT%H:%M'

        return self.client.post(
            reverse('reschedule_reservation', args=[reservation.pk]),
            {
                'start_time': start.strftime(fmt),
                'end_time': end.strftime(fmt),
                'reason': reason
            }
        )

    def make_closure(self, start, end):
        return FacilityClosure.objects.create(
            facility=self.facility,
            start_time=start,
            end_time=end,
            reason='Maintenance',
            is_active=True
        )


class ApprovalRejectionTests(AdminBookingTestBase):

    def assert_unchanged(self, reservation, status):
        reservation.refresh_from_db()

        self.assertEqual(reservation.status, status)
        self.assertEqual(ReservationChange.objects.count(), 0)
        self.assertEqual(AuditLog.objects.count(), 0)

    def test_approve_without_reason_is_blocked(self):
        reservation = self.book(self.at(9), self.at(11), status='pending')
        self.decide(reservation, 'approve', reason='')
        self.assert_unchanged(reservation, 'pending')

    def test_reject_without_reason_is_blocked(self):
        reservation = self.book(self.at(9), self.at(11), status='pending')
        self.decide(reservation, 'reject', reason='   ')
        self.assert_unchanged(reservation, 'pending')

    def test_invalid_action_is_rejected(self):
        reservation = self.book(self.at(9), self.at(11), status='pending')
        self.decide(reservation, 'DELETE')
        self.assert_unchanged(reservation, 'pending')

    def test_reject_requires_pending_status(self):
        reservation = self.book(self.at(9), self.at(11))
        self.decide(reservation, 'reject')
        self.assert_unchanged(reservation, 'approved')

    def test_approve_requires_pending_status(self):
        reservation = self.book(self.at(9), self.at(11))
        self.decide(reservation, 'approve')
        self.assert_unchanged(reservation, 'approved')

    def test_rejected_reservation_cannot_be_approved_later(self):
        reservation = self.book(self.at(9), self.at(11), status='rejected')
        self.decide(reservation, 'approve')
        self.assert_unchanged(reservation, 'rejected')

    def test_approving_reservation_in_the_past_is_blocked(self):
        now = timezone.now()

        reservation = self.book(
            now - timedelta(hours=2),
            now - timedelta(hours=1),
            status='pending'
        )

        self.decide(reservation, 'approve')
        self.assert_unchanged(reservation, 'pending')

    def test_unknown_reservation_returns_404(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('update_reservation_status', args=[999999]),
            {'action': 'approve', 'reason': 'Test reason'}
        )

        self.assertEqual(response.status_code, 404)

    def test_rejection_records_decision_details(self):
        reservation = self.book(self.at(9), self.at(11), status='pending')

        self.decide(reservation, 'reject', reason='Room reserved for exams')

        reservation.refresh_from_db()

        self.assertEqual(reservation.status, 'rejected')
        self.assertEqual(reservation.decision_by, self.admin)
        self.assertEqual(reservation.decision_reason, 'Room reserved for exams')
        self.assertIsNotNone(reservation.decision_at)

        self.assertTrue(
            AuditLog.objects.filter(
                admin_user=self.admin,
                action='REJECT',
                model_name='Reservation',
                object_id=reservation.pk,
                description__contains='Room reserved for exams'
            ).exists()
        )

    def test_admin_can_cancel_approved_reservation(self):
        reservation = self.book(self.at(9), self.at(11))

        self.decide(reservation, 'cancel', reason='Event called off')

        reservation.refresh_from_db()
        self.assertEqual(reservation.status, 'cancelled')

        self.assertTrue(
            ReservationChange.objects.filter(
                reservation=reservation,
                previous_status='approved',
                new_status='cancelled',
                changed_by=self.admin
            ).exists()
        )

        self.assertTrue(
            AuditLog.objects.filter(
                admin_user=self.admin,
                action='CANCEL',
                object_id=reservation.pk
            ).exists()
        )

    def test_admin_cancel_requires_reason(self):
        reservation = self.book(self.at(9), self.at(11))
        self.decide(reservation, 'cancel', reason='')
        self.assert_unchanged(reservation, 'approved')

    def test_admin_cannot_cancel_pending_reservation(self):
        reservation = self.book(self.at(9), self.at(11), status='pending')
        self.decide(reservation, 'cancel')
        self.assert_unchanged(reservation, 'pending')


class ReschedulingTests(AdminBookingTestBase):

    def assert_not_rescheduled(self, reservation, start, end):
        reservation.refresh_from_db()

        self.assertEqual(reservation.start_time, start)
        self.assertEqual(reservation.end_time, end)

        self.assertFalse(
            ReservationChange.objects.filter(
                reservation=reservation
            ).exists()
        )

        self.assertFalse(
            AuditLog.objects.filter(action='UPDATE').exists()
        )

    def test_same_schedule_is_blocked(self):
        reservation = self.book(self.at(9), self.at(11))
        self.reschedule(reservation, self.at(9), self.at(11))
        self.assert_not_rescheduled(reservation, self.at(9), self.at(11))

    def test_reschedule_requires_reason(self):
        reservation = self.book(self.at(9), self.at(11))
        self.reschedule(reservation, self.at(13), self.at(15), reason='   ')
        self.assert_not_rescheduled(reservation, self.at(9), self.at(11))

    def test_only_approved_reservations_can_be_rescheduled(self):
        reservation = self.book(self.at(9), self.at(11), status='pending')
        self.reschedule(reservation, self.at(13), self.at(15))
        self.assert_not_rescheduled(reservation, self.at(9), self.at(11))

    def test_started_reservation_cannot_be_rescheduled(self):
        start = timezone.now() - timedelta(minutes=30)
        end = timezone.now() + timedelta(minutes=30)

        reservation = self.book(start, end)

        self.reschedule(reservation, self.at(13), self.at(15))
        self.assert_not_rescheduled(reservation, start, end)

    def test_outside_operating_hours_is_blocked(self):
        reservation = self.book(self.at(9), self.at(11))
        self.reschedule(reservation, self.at(7), self.at(9))
        self.assert_not_rescheduled(reservation, self.at(9), self.at(11))

    def test_reschedule_into_closure_is_blocked(self):
        self.make_closure(self.at(13), self.at(15))

        reservation = self.book(self.at(9), self.at(11))

        self.reschedule(reservation, self.at(13), self.at(15))
        self.assert_not_rescheduled(reservation, self.at(9), self.at(11))

    def test_invalid_dates_are_blocked(self):
        reservation = self.book(self.at(9), self.at(11))

        self.client.force_login(self.admin)

        self.client.post(
            reverse('reschedule_reservation', args=[reservation.pk]),
            {
                'start_time': 'not-a-date',
                'end_time': 'also-not-a-date',
                'reason': 'Test reason'
            }
        )

        self.assert_not_rescheduled(reservation, self.at(9), self.at(11))

    def test_reschedule_overlapping_own_old_slot_is_allowed(self):
        reservation = self.book(self.at(9), self.at(11))

        self.reschedule(reservation, self.at(10), self.at(12))

        reservation.refresh_from_db()

        self.assertEqual(reservation.start_time, self.at(10))
        self.assertEqual(reservation.end_time, self.at(12))
        self.assertEqual(reservation.status, 'approved')

        self.assertTrue(
            ReservationChange.objects.filter(
                reservation=reservation,
                previous_start_time=self.at(9),
                new_start_time=self.at(10)
            ).exists()
        )

    def test_reschedule_next_to_another_booking_is_allowed(self):
        self.book(self.at(11), self.at(13), user=self.other_user)

        reservation = self.book(self.at(9), self.at(11))

        self.reschedule(reservation, self.at(13), self.at(15))

        reservation.refresh_from_db()
        self.assertEqual(reservation.start_time, self.at(13))

    def test_reschedule_is_recorded_in_audit_log(self):
        reservation = self.book(self.at(9), self.at(11))

        self.reschedule(reservation, self.at(13), self.at(15))

        self.assertTrue(
            AuditLog.objects.filter(
                admin_user=self.admin,
                action='UPDATE',
                model_name='Reservation',
                object_id=reservation.pk,
                description__contains='Rescheduled reservation'
            ).exists()
        )


class FacilityClosureRuleTests(AdminBookingTestBase):

    def new_closure(self, start, end):
        return FacilityClosure(
            facility=self.facility,
            start_time=start,
            end_time=end,
            reason='Maintenance',
            is_active=True
        )

    def test_closure_in_the_past_is_blocked(self):
        now = timezone.now()

        with self.assertRaises(ValidationError):
            self.new_closure(
                now - timedelta(hours=2),
                now - timedelta(hours=1)
            ).full_clean()

    def test_closure_end_before_start_is_blocked(self):
        with self.assertRaises(ValidationError):
            self.new_closure(self.at(14), self.at(13)).full_clean()

    def test_overlapping_closures_are_blocked(self):
        self.make_closure(self.at(13), self.at(15))

        with self.assertRaises(ValidationError):
            self.new_closure(self.at(14), self.at(16)).full_clean()

    def test_adjacent_closures_are_allowed(self):
        self.make_closure(self.at(13), self.at(15))
        self.new_closure(self.at(15), self.at(17)).full_clean()

    def test_closure_conflicts_with_checked_in_reservation(self):
        self.book(self.at(9), self.at(11), status='checked_in')

        with self.assertRaises(ValidationError):
            self.new_closure(self.at(10), self.at(12)).full_clean()

    def test_closure_over_pending_reservation_is_allowed(self):
        self.book(self.at(9), self.at(11), status='pending')
        self.new_closure(self.at(10), self.at(12)).full_clean()

    def test_pending_reservation_under_closure_cannot_be_approved(self):
        reservation = self.book(self.at(10), self.at(11), status='pending')

        self.make_closure(self.at(9), self.at(12))

        self.decide(reservation, 'approve')

        reservation.refresh_from_db()
        self.assertEqual(reservation.status, 'pending')

    def test_admin_can_archive_closure(self):
        closure = self.make_closure(self.at(13), self.at(15))

        self.client.force_login(self.admin)

        self.client.post(reverse('archive_closure', args=[closure.pk]))

        closure.refresh_from_db()
        self.assertFalse(closure.is_active)

        self.assertTrue(
            AuditLog.objects.filter(
                admin_user=self.admin,
                action='ARCHIVE',
                model_name='FacilityClosure',
                object_id=closure.pk
            ).exists()
        )

    def test_archiving_twice_creates_one_audit_entry(self):
        closure = self.make_closure(self.at(13), self.at(15))

        self.client.force_login(self.admin)

        url = reverse('archive_closure', args=[closure.pk])

        self.client.post(url)
        self.client.post(url)

        self.assertEqual(
            AuditLog.objects.filter(action='ARCHIVE').count(),
            1
        )

    def test_basic_user_cannot_archive_closure(self):
        closure = self.make_closure(self.at(13), self.at(15))

        self.client.force_login(self.user)

        response = self.client.post(
            reverse('archive_closure', args=[closure.pk])
        )

        self.assertEqual(response.status_code, 403)

        closure.refresh_from_db()
        self.assertTrue(closure.is_active)