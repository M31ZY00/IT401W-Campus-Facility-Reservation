from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

from management.models import AuditLog
from reservations.models import EventIncident, EventRecord, ReservationChange
from reservations.test_approvals_closures import AdminBookingTestBase


class EventTestBase(AdminBookingTestBase):

    def live(self, status='approved'):
        now = timezone.now()

        return self.book(
            now - timedelta(minutes=30),
            now + timedelta(minutes=30),
            status=status
        )

    def ended(self, status='approved'):
        now = timezone.now()

        return self.book(
            now - timedelta(hours=3),
            now - timedelta(hours=1),
            status=status
        )

    def checked_in(self):
        reservation = self.live(status='checked_in')

        EventRecord.objects.create(
            reservation=reservation,
            actual_start=timezone.now() - timedelta(minutes=20),
            checked_in_by=self.admin
        )

        return reservation

    def act(self, reservation, action, reason=''):
        return self.decide(reservation, action, reason=reason)

    def run_lifecycle(self):
        reservation = self.live()

        self.act(reservation, 'CHECK_IN')
        self.act(reservation, 'COMPLETE')

        return reservation

    def assert_untouched(self, reservation, status):
        reservation.refresh_from_db()

        self.assertEqual(reservation.status, status)
        self.assertEqual(ReservationChange.objects.count(), 0)
        self.assertEqual(AuditLog.objects.count(), 0)

    def report_incident(self, reservation, description='Projector failed'):
        self.client.force_login(self.admin)

        return self.client.post(
            reverse('report_event_incident', args=[reservation.pk]),
            {'description': description}
        )


class CheckInRuleTests(EventTestBase):

    def test_pending_reservation_cannot_be_checked_in(self):
        reservation = self.live(status='pending')
        self.act(reservation, 'CHECK_IN')
        self.assert_untouched(reservation, 'pending')
        self.assertEqual(EventRecord.objects.count(), 0)

    def test_cancelled_reservation_cannot_be_checked_in(self):
        reservation = self.live(status='cancelled')
        self.act(reservation, 'CHECK_IN')
        self.assert_untouched(reservation, 'cancelled')

    def test_rejected_reservation_cannot_be_checked_in(self):
        reservation = self.live(status='rejected')
        self.act(reservation, 'CHECK_IN')
        self.assert_untouched(reservation, 'rejected')

    def test_double_check_in_is_blocked(self):
        reservation = self.live()

        self.act(reservation, 'CHECK_IN')
        self.act(reservation, 'CHECK_IN')

        reservation.refresh_from_db()

        self.assertEqual(reservation.status, 'checked_in')
        self.assertEqual(ReservationChange.objects.count(), 1)
        self.assertEqual(AuditLog.objects.filter(action='CHECK_IN').count(), 1)

    def test_check_in_records_details_and_reason(self):
        reservation = self.live()

        self.act(reservation, 'CHECK_IN', reason='Organizer arrived on time')

        reservation.refresh_from_db()
        record = EventRecord.objects.get(reservation=reservation)

        self.assertEqual(reservation.status, 'checked_in')
        self.assertEqual(record.checked_in_by, self.admin)
        self.assertIsNotNone(record.actual_start)
        self.assertIsNone(record.actual_end)

        self.assertTrue(
            ReservationChange.objects.filter(
                reservation=reservation,
                previous_status='approved',
                new_status='checked_in',
                reason='Organizer arrived on time'
            ).exists()
        )

        self.assertTrue(
            AuditLog.objects.filter(
                action='CHECK_IN',
                description__contains='Reason: Organizer arrived on time'
            ).exists()
        )

    def test_check_in_without_reason_is_allowed(self):
        reservation = self.live()

        self.act(reservation, 'CHECK_IN')

        reservation.refresh_from_db()
        self.assertEqual(reservation.status, 'checked_in')

        log = AuditLog.objects.get(action='CHECK_IN')
        self.assertNotIn('Reason:', log.description)


class CompletionRuleTests(EventTestBase):

    def test_cannot_complete_twice(self):
        reservation = self.checked_in()

        self.act(reservation, 'COMPLETE')
        self.act(reservation, 'COMPLETE')

        reservation.refresh_from_db()

        self.assertEqual(reservation.status, 'completed')
        self.assertEqual(ReservationChange.objects.count(), 1)
        self.assertEqual(AuditLog.objects.filter(action='COMPLETE').count(), 1)

    def test_complete_checked_in_without_event_record_is_blocked(self):
        reservation = self.live(status='checked_in')

        self.act(reservation, 'COMPLETE')

        self.assert_untouched(reservation, 'checked_in')
        self.assertEqual(EventRecord.objects.count(), 0)

    def test_complete_with_incomplete_check_in_record_is_blocked(self):
        reservation = self.live(status='checked_in')

        record = EventRecord.objects.create(reservation=reservation)

        self.act(reservation, 'COMPLETE')

        self.assert_untouched(reservation, 'checked_in')

        record.refresh_from_db()
        self.assertIsNone(record.actual_end)

    def test_completion_records_end_time_and_actor(self):
        reservation = self.checked_in()

        self.act(reservation, 'COMPLETE')

        record = EventRecord.objects.get(reservation=reservation)

        self.assertIsNotNone(record.actual_end)
        self.assertGreaterEqual(record.actual_end, record.actual_start)
        self.assertEqual(record.completed_by, self.admin)

    def test_completed_event_cannot_be_checked_in_again(self):
        reservation = self.live(status='completed')
        self.act(reservation, 'CHECK_IN')
        self.assert_untouched(reservation, 'completed')


class NoShowRuleTests(EventTestBase):

    def test_no_show_on_completed_event_is_blocked(self):
        reservation = self.ended(status='completed')
        self.act(reservation, 'NO_SHOW')
        self.assert_untouched(reservation, 'completed')

    def test_no_show_on_pending_reservation_is_blocked(self):
        reservation = self.ended(status='pending')
        self.act(reservation, 'NO_SHOW')
        self.assert_untouched(reservation, 'pending')

    def test_no_show_twice_is_blocked(self):
        reservation = self.ended()

        self.act(reservation, 'NO_SHOW')
        self.act(reservation, 'NO_SHOW')

        reservation.refresh_from_db()

        self.assertEqual(reservation.status, 'no_show')
        self.assertEqual(ReservationChange.objects.count(), 1)
        self.assertEqual(AuditLog.objects.filter(action='NO_SHOW').count(), 1)

    def test_no_show_records_actor_and_time(self):
        reservation = self.ended()

        self.act(reservation, 'NO_SHOW')

        record = EventRecord.objects.get(reservation=reservation)

        self.assertIsNotNone(record.no_show_at)
        self.assertEqual(record.no_show_marked_by, self.admin)
        self.assertIsNone(record.actual_start)

        self.assertTrue(
            ReservationChange.objects.filter(
                reservation=reservation,
                previous_status='approved',
                new_status='no_show'
            ).exists()
        )

    def test_no_show_event_cannot_be_checked_in(self):
        reservation = self.ended(status='no_show')
        self.act(reservation, 'CHECK_IN')
        self.assert_untouched(reservation, 'no_show')


class AuditRecordTests(EventTestBase):

    def audit_page(self, **params):
        self.client.force_login(self.admin)

        return self.client.get(reverse('view_audit_logs'), params)

    def test_full_lifecycle_creates_matching_history_and_audit(self):
        reservation = self.run_lifecycle()

        reservation.refresh_from_db()
        self.assertEqual(reservation.status, 'completed')

        changes = {
            (change.previous_status, change.new_status)
            for change in ReservationChange.objects.filter(
                reservation=reservation
            )
        }

        self.assertEqual(
            changes,
            {('approved', 'checked_in'), ('checked_in', 'completed')}
        )

        logs = AuditLog.objects.all()

        self.assertEqual(
            {log.action for log in logs},
            {'CHECK_IN', 'COMPLETE'}
        )

        for log in logs:
            self.assertEqual(log.admin_user, self.admin)
            self.assertEqual(log.model_name, 'Reservation')
            self.assertEqual(log.object_id, reservation.pk)

    def test_audit_description_names_facility_and_requester(self):
        reservation = self.live()

        self.act(reservation, 'CHECK_IN')

        log = AuditLog.objects.get(action='CHECK_IN')

        self.assertIn(f'#{reservation.pk}', log.description)
        self.assertIn(self.facility.name, log.description)
        self.assertIn(self.user.username, log.description)

    def test_failed_actions_leave_no_audit_entry(self):
        cases = [
            ('pending', 'CHECK_IN'),
            ('pending', 'COMPLETE'),
            ('pending', 'NO_SHOW'),
            ('cancelled', 'CHECK_IN'),
            ('rejected', 'NO_SHOW'),
        ]

        for status, action in cases:
            with self.subTest(status=status, action=action):
                from reservations.models import Reservation

                Reservation.objects.all().delete()

                reservation = self.live(status=status)

                self.act(reservation, action)

                self.assertEqual(AuditLog.objects.count(), 0)

    def test_audit_page_filters_by_action(self):
        self.run_lifecycle()

        everything = self.audit_page()
        check_ins = self.audit_page(action='CHECK_IN')
        completions = self.audit_page(action='COMPLETE')

        self.assertEqual(everything.context['total_logs'], 2)
        self.assertEqual(check_ins.context['total_logs'], 1)
        self.assertEqual(completions.context['total_logs'], 1)

        for log in check_ins.context['page_obj']:
            self.assertEqual(log.action, 'CHECK_IN')

    def test_audit_page_search_finds_reservation_entries(self):
        reservation = self.run_lifecycle()

        response = self.audit_page(search=str(reservation.pk))

        self.assertEqual(response.context['total_logs'], 2)

    def test_audit_page_ignores_invalid_action_filter(self):
        self.run_lifecycle()

        response = self.audit_page(action='NOT_AN_ACTION')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_logs'], 2)

    def test_audit_page_date_filter(self):
        self.run_lifecycle()

        today = timezone.localdate()
        tomorrow = today + timedelta(days=1)

        from_today = self.audit_page(date_from=today.isoformat())
        from_tomorrow = self.audit_page(date_from=tomorrow.isoformat())

        self.assertEqual(from_today.context['total_logs'], 2)
        self.assertEqual(from_tomorrow.context['total_logs'], 0)


class IncidentRuleTests(EventTestBase):

    def test_incident_allowed_for_completed_event(self):
        reservation = self.checked_in()

        self.act(reservation, 'COMPLETE')

        self.report_incident(reservation)

        incident = EventIncident.objects.get()

        self.assertEqual(incident.reported_by, self.admin)

        self.assertTrue(
            AuditLog.objects.filter(
                action='CREATE',
                model_name='EventIncident',
                object_id=incident.pk
            ).exists()
        )

    def test_incident_allowed_for_no_show_event(self):
        reservation = self.ended()

        self.act(reservation, 'NO_SHOW')

        self.report_incident(reservation)

        self.assertEqual(EventIncident.objects.count(), 1)

    def test_incident_blocked_for_approved_reservation(self):
        reservation = self.live()

        self.report_incident(reservation)

        self.assertEqual(EventIncident.objects.count(), 0)

    def test_incident_blocked_for_cancelled_reservation(self):
        reservation = self.live(status='cancelled')

        self.report_incident(reservation)

        self.assertEqual(EventIncident.objects.count(), 0)

    def test_incident_blocked_when_event_record_is_missing(self):
        reservation = self.live(status='checked_in')

        self.report_incident(reservation)

        self.assertEqual(EventIncident.objects.count(), 0)
        self.assertEqual(EventRecord.objects.count(), 0)


class EventPageTests(EventTestBase):

    def test_event_monitoring_lists_only_booked_statuses(self):
        approved = self.book(self.at(9), self.at(10))
        self.book(self.at(11), self.at(12), status='pending')
        self.book(self.at(13), self.at(14), status='cancelled')

        self.client.force_login(self.admin)

        response = self.client.get(
            reverse('event_monitoring'),
            {'date': self.event_date.isoformat()}
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            [r.pk for r in response.context['reservations']],
            [approved.pk]
        )

    def test_event_monitoring_invalid_date_falls_back_to_today(self):
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse('event_monitoring'),
            {'date': 'not-a-date'}
        )

        self.assertEqual(response.status_code, 200)

    def test_printable_slip_blocked_for_pending_reservation(self):
        reservation = self.book(self.at(9), self.at(10), status='pending')

        self.client.force_login(self.admin)

        response = self.client.get(
            reverse('printable_event_slip', args=[reservation.pk])
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('event_monitoring'))

    def test_printable_slip_available_for_no_show_event(self):
        reservation = self.ended(status='no_show')

        self.client.force_login(self.admin)

        response = self.client.get(
            reverse('printable_event_slip', args=[reservation.pk])
        )

        self.assertEqual(response.status_code, 200)

    def test_event_detail_loads_without_event_record(self):
        reservation = self.book(self.at(9), self.at(10))

        self.client.force_login(self.admin)

        response = self.client.get(
            reverse('event_detail', args=[reservation.pk])
        )

        self.assertEqual(response.status_code, 200)

    def test_basic_user_cannot_open_event_pages(self):
        reservation = self.book(self.at(9), self.at(10))

        self.client.force_login(self.user)

        urls = [
            reverse('event_monitoring'),
            reverse('event_detail', args=[reservation.pk]),
            reverse('printable_event_slip', args=[reservation.pk]),
        ]

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)

                self.assertEqual(response.status_code, 403)