from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from facilities.models import Facility, FacilityCategory, FacilityClosure
from management.models import AuditLog, SystemSetting
from reservations.models import Reservation, ReservationChange


class ReservationWorkflowTests(TestCase):

    def setUp(self):

        User = get_user_model()

        self.basic_user = User.objects.create_user(
            username='workflowuser',
            email='workflow@example.com',
            password='TestPassword123!'
        )

        self.admin_user = User.objects.create_user(
            username='workflowadmin',
            email='workflowadmin@example.com',
            password='AdminPassword123!',
            is_staff=True
        )

        self.category = FacilityCategory.objects.create(
            name='Conference Rooms',
            description='Rooms for campus meetings'
        )

        self.facility = Facility.objects.create(
            category=self.category,
            code='TEST-ROOM-001',
            name='Testing Conference Room',
            location='Main Building',
            capacity=50,
            opening_time=time(8, 0),
            closing_time=time(17, 0),
            is_active=True
        )

        self.setting = SystemSetting.get_current()

        self.setting.max_booking_hours = 4
        self.setting.advance_booking_days = 30
        self.setting.save()

        self.event_date = timezone.localdate() + timedelta(days=5)

        self.start_time = self.make_datetime(9)
        self.end_time = self.make_datetime(11)

    def make_datetime(self, hour, minute=0):

        return timezone.make_aware(
            datetime.combine(
                self.event_date,
                time(hour, minute)
            ),
            ZoneInfo('Asia/Manila')
        )

    def make_reservation(
        self,
        start_time=None,
        end_time=None,
        status='pending',
        participant_count=20
    ):

        return Reservation.objects.create(
            user=self.basic_user,
            facility=self.facility,
            event_title='Automated Test Event',
            purpose='Testing reservation workflow',
            participant_count=participant_count,
            start_time=start_time or self.start_time,
            end_time=end_time or self.end_time,
            status=status
        )

    def admin_update(self, reservation, action, reason='Test decision'):

        self.client.force_login(self.admin_user)

        return self.client.post(
            reverse(
                'update_reservation_status',
                args=[reservation.pk]
            ),
            {
                'action': action,
                'reason': reason
            }
        )

    def test_basic_user_can_create_reservation(self):

        self.client.force_login(self.basic_user)

        response = self.client.post(
            reverse(
                'create_reservation',
                args=[self.facility.pk]
            ),
            {
                'event_title': 'Student Conference',
                'purpose': 'Academic conference',
                'participant_count': 20,
                'start_time': self.start_time.strftime(
                    '%Y-%m-%dT%H:%M'
                ),
                'end_time': self.end_time.strftime(
                    '%Y-%m-%dT%H:%M'
                )
            }
        )

        self.assertEqual(response.status_code, 302)

        reservation = Reservation.objects.get(
            user=self.basic_user
        )

        self.assertEqual(
            reservation.status,
            'pending'
        )

        self.assertEqual(
            reservation.facility,
            self.facility
        )

        self.assertEqual(
            reservation.participant_count,
            20
        )

    def test_admin_can_approve_reservation(self):

        reservation = self.make_reservation()

        response = self.admin_update(
            reservation,
            'approve',
            'Approved for testing'
        )

        self.assertEqual(response.status_code, 302)

        reservation.refresh_from_db()

        self.assertEqual(
            reservation.status,
            'approved'
        )

        self.assertEqual(
            reservation.decision_by,
            self.admin_user
        )

        self.assertIsNotNone(
            reservation.decision_at
        )

        self.assertTrue(
            ReservationChange.objects.filter(
                reservation=reservation,
                previous_status='pending',
                new_status='approved',
                changed_by=self.admin_user
            ).exists()
        )

        self.assertTrue(
            AuditLog.objects.filter(
                admin_user=self.admin_user,
                action='APPROVE'
            ).exists()
        )

    def test_admin_can_reject_reservation(self):

        reservation = self.make_reservation()

        response = self.admin_update(
            reservation,
            'reject',
            'Facility unavailable for this event'
        )

        self.assertEqual(response.status_code, 302)

        reservation.refresh_from_db()

        self.assertEqual(
            reservation.status,
            'rejected'
        )

        self.assertTrue(
            ReservationChange.objects.filter(
                reservation=reservation,
                previous_status='pending',
                new_status='rejected',
                changed_by=self.admin_user
            ).exists()
        )

        self.assertTrue(
            AuditLog.objects.filter(
                admin_user=self.admin_user,
                action='REJECT'
            ).exists()
        )

    def test_overlapping_pending_reservations_are_allowed(self):

        first_reservation = self.make_reservation()

        second_reservation = self.make_reservation(
            start_time=self.make_datetime(10),
            end_time=self.make_datetime(12)
        )

        first_reservation.full_clean()
        second_reservation.full_clean()

        self.assertEqual(
            Reservation.objects.filter(
                status='pending'
            ).count(),
            2
        )

    def test_overlapping_approved_reservations_are_prevented(self):

        self.make_reservation(
            status='approved'
        )

        conflicting_reservation = self.make_reservation(
            start_time=self.make_datetime(10),
            end_time=self.make_datetime(12),
            status='approved'
        )

        with self.assertRaises(ValidationError):

            conflicting_reservation.full_clean()

    def test_adjacent_approved_reservations_are_allowed(self):

        first_reservation = self.make_reservation(
            start_time=self.make_datetime(9),
            end_time=self.make_datetime(11),
            status='approved'
        )

        second_reservation = self.make_reservation(
            start_time=self.make_datetime(11),
            end_time=self.make_datetime(13),
            status='approved'
        )

        first_reservation.full_clean()
        second_reservation.full_clean()

        self.assertEqual(
            Reservation.objects.filter(
                status='approved'
            ).count(),
            2
        )

    def test_reservation_exceeding_maximum_duration_is_rejected(self):

        reservation = self.make_reservation(
            start_time=self.make_datetime(9),
            end_time=self.make_datetime(14)
        )

        with self.assertRaises(ValidationError):

            reservation.full_clean()

    def test_reservation_exceeding_advance_window_is_rejected(self):

        future_date = timezone.localdate() + timedelta(days=40)

        start_time = timezone.make_aware(
            datetime.combine(
                future_date,
                time(9, 0)
            ),
            ZoneInfo('Asia/Manila')
        )

        end_time = timezone.make_aware(
            datetime.combine(
                future_date,
                time(11, 0)
            ),
            ZoneInfo('Asia/Manila')
        )

        reservation = self.make_reservation(
            start_time=start_time,
            end_time=end_time
        )

        with self.assertRaises(ValidationError):

            reservation.full_clean()

    def test_reservation_exceeding_capacity_is_rejected(self):

        reservation = self.make_reservation(
            participant_count=100
        )

        with self.assertRaises(ValidationError):

            reservation.full_clean()

    def test_basic_user_cannot_approve_reservation(self):

        reservation = self.make_reservation()

        self.client.force_login(
            self.basic_user
        )

        response = self.client.post(
            reverse(
                'update_reservation_status',
                args=[reservation.pk]
            ),
            {
                'action': 'approve',
                'reason': 'Unauthorized approval'
            }
        )

        self.assertEqual(
            response.status_code,
            403
        )

        reservation.refresh_from_db()

        self.assertEqual(
            reservation.status,
            'pending'
        )

    def test_admin_cannot_approve_conflicting_reservation(self):

        self.make_reservation(
            status='approved'
        )

        conflicting_reservation = self.make_reservation(
            start_time=self.make_datetime(10),
            end_time=self.make_datetime(12)
        )

        response = self.admin_update(
            conflicting_reservation,
            'approve',
            'Attempting conflicting approval'
        )

        self.assertEqual(
            response.status_code,
            302
        )

        conflicting_reservation.refresh_from_db()

        self.assertEqual(
            conflicting_reservation.status,
            'pending'
        )

        self.assertFalse(
            ReservationChange.objects.filter(
                reservation=conflicting_reservation,
                new_status='approved'
            ).exists()
        )

    def test_reservation_during_facility_closure_is_rejected(self):

        FacilityClosure.objects.create(
            facility=self.facility,
            start_time=self.make_datetime(9),
            end_time=self.make_datetime(12),
            reason='Scheduled maintenance',
            is_active=True
        )

        reservation = self.make_reservation(
            start_time=self.make_datetime(10),
            end_time=self.make_datetime(11)
        )

        with self.assertRaises(ValidationError):

            reservation.full_clean()

class AdvancedSchedulingTests(TestCase):

    def setUp(self):

        User = get_user_model()

        self.basic_user = User.objects.create_user(
            username='schedulinguser',
            email='scheduling@example.com',
            password='TestPassword123!'
        )

        self.admin_user = User.objects.create_user(
            username='schedulingadmin',
            email='schedulingadmin@example.com',
            password='AdminPassword123!',
            is_staff=True
        )

        self.category = FacilityCategory.objects.create(
            name='Lecture Rooms',
            description='Rooms for academic activities',
            is_active=True
        )

        self.facility = Facility.objects.create(
            category=self.category,
            code='SCHEDULE-001',
            name='Scheduling Test Room',
            location='Academic Building',
            capacity=50,
            opening_time=time(8, 0),
            closing_time=time(17, 0),
            is_active=True
        )

        system_setting = SystemSetting.get_current()

        system_setting.max_booking_hours = 4
        system_setting.advance_booking_days = 30

        system_setting.save()

        self.event_date = timezone.localdate() + timedelta(days=5)

        self.start_time = self.make_datetime(9)
        self.end_time = self.make_datetime(11)

    def make_datetime(self, hour, minute=0, event_date=None):

        selected_date = event_date or self.event_date

        return timezone.make_aware(
            datetime.combine(
                selected_date,
                time(hour, minute)
            ),
            ZoneInfo('Asia/Manila')
        )

    def make_reservation(
        self,
        start_time=None,
        end_time=None,
        status='pending',
        participant_count=20
    ):

        return Reservation.objects.create(
            user=self.basic_user,
            facility=self.facility,
            event_title='Advanced Scheduling Test',
            purpose='Testing facility scheduling rules',
            participant_count=participant_count,
            start_time=start_time or self.start_time,
            end_time=end_time or self.end_time,
            status=status
        )

    def test_inactive_facility_rejects_reservation(self):

        self.facility.is_active = False

        self.facility.save(
            update_fields=['is_active']
        )

        reservation = self.make_reservation()

        with self.assertRaises(ValidationError):
            reservation.full_clean()

    def test_inactive_category_rejects_reservation(self):

        self.category.is_active = False

        self.category.save(
            update_fields=['is_active']
        )

        reservation = self.make_reservation()

        with self.assertRaises(ValidationError):
            reservation.full_clean()

    def test_reservation_before_opening_hours_is_rejected(self):

        reservation = self.make_reservation(
            start_time=self.make_datetime(7),
            end_time=self.make_datetime(9)
        )

        with self.assertRaises(ValidationError):
            reservation.full_clean()

    def test_reservation_after_closing_hours_is_rejected(self):

        reservation = self.make_reservation(
            start_time=self.make_datetime(16),
            end_time=self.make_datetime(18)
        )

        with self.assertRaises(ValidationError):
            reservation.full_clean()

    def test_overnight_reservation_is_rejected(self):

        next_day = self.event_date + timedelta(days=1)

        reservation = self.make_reservation(
            start_time=self.make_datetime(16),
            end_time=self.make_datetime(
                9,
                event_date=next_day
            )
        )

        with self.assertRaises(ValidationError):
            reservation.full_clean()

    def test_past_reservation_is_rejected(self):

        past_date = timezone.localdate() - timedelta(days=1)

        reservation = self.make_reservation(
            start_time=self.make_datetime(
                9,
                event_date=past_date
            ),
            end_time=self.make_datetime(
                11,
                event_date=past_date
            )
        )

        with self.assertRaises(ValidationError):
            reservation.full_clean()

    def test_zero_participants_is_rejected(self):

        reservation = self.make_reservation(
            participant_count=0
        )

        with self.assertRaises(ValidationError):
            reservation.full_clean()

    def test_active_closure_blocks_reservation(self):

        FacilityClosure.objects.create(
            facility=self.facility,
            start_time=self.make_datetime(9),
            end_time=self.make_datetime(12),
            reason='Facility maintenance',
            is_active=True
        )

        reservation = self.make_reservation(
            start_time=self.make_datetime(10),
            end_time=self.make_datetime(11)
        )

        with self.assertRaises(ValidationError):
            reservation.full_clean()

    def test_archived_closure_does_not_block_reservation(self):

        FacilityClosure.objects.create(
            facility=self.facility,
            start_time=self.make_datetime(9),
            end_time=self.make_datetime(12),
            reason='Cancelled maintenance',
            is_active=False
        )

        reservation = self.make_reservation(
            start_time=self.make_datetime(10),
            end_time=self.make_datetime(11)
        )

        reservation.full_clean()

        self.assertEqual(
            reservation.status,
            'pending'
        )

    def test_adjacent_closure_does_not_block_reservation(self):

        FacilityClosure.objects.create(
            facility=self.facility,
            start_time=self.make_datetime(11),
            end_time=self.make_datetime(13),
            reason='Scheduled maintenance',
            is_active=True
        )

        reservation = self.make_reservation(
            start_time=self.make_datetime(9),
            end_time=self.make_datetime(11)
        )

        reservation.full_clean()

        self.assertEqual(
            reservation.status,
            'pending'
        )

    def test_closure_cannot_overlap_approved_reservation(self):

        self.make_reservation(
            start_time=self.make_datetime(9),
            end_time=self.make_datetime(11),
            status='approved'
        )

        closure = FacilityClosure(
            facility=self.facility,
            start_time=self.make_datetime(10),
            end_time=self.make_datetime(12),
            reason='Conflicting maintenance',
            is_active=True
        )

        with self.assertRaises(ValidationError):
            closure.full_clean()

    def test_admin_can_reschedule_approved_reservation(self):

        reservation = self.make_reservation(
            status='approved'
        )

        new_start = self.make_datetime(13)
        new_end = self.make_datetime(15)

        self.client.force_login(
            self.admin_user
        )

        response = self.client.post(
            reverse(
                'reschedule_reservation',
                args=[reservation.pk]
            ),
            {
                'start_time': new_start.strftime(
                    '%Y-%m-%dT%H:%M'
                ),
                'end_time': new_end.strftime(
                    '%Y-%m-%dT%H:%M'
                ),
                'reason': 'Updated event schedule'
            }
        )

        self.assertEqual(
            response.status_code,
            302
        )

        reservation.refresh_from_db()

        self.assertEqual(
            reservation.start_time,
            new_start
        )

        self.assertEqual(
            reservation.end_time,
            new_end
        )

        self.assertEqual(
            reservation.status,
            'approved'
        )

        self.assertTrue(
            ReservationChange.objects.filter(
                reservation=reservation,
                changed_by=self.admin_user,
                previous_start_time=self.start_time,
                previous_end_time=self.end_time,
                new_start_time=new_start,
                new_end_time=new_end
            ).exists()
        )

    def test_admin_cannot_reschedule_into_occupied_slot(self):

        self.make_reservation(
            start_time=self.make_datetime(13),
            end_time=self.make_datetime(15),
            status='approved'
        )

        reservation = self.make_reservation(
            start_time=self.make_datetime(9),
            end_time=self.make_datetime(11),
            status='approved'
        )

        original_start = reservation.start_time
        original_end = reservation.end_time

        self.client.force_login(
            self.admin_user
        )

        response = self.client.post(
            reverse(
                'reschedule_reservation',
                args=[reservation.pk]
            ),
            {
                'start_time': self.make_datetime(13).strftime(
                    '%Y-%m-%dT%H:%M'
                ),
                'end_time': self.make_datetime(15).strftime(
                    '%Y-%m-%dT%H:%M'
                ),
                'reason': 'Attempting conflicting reschedule'
            }
        )

        self.assertIn(
            response.status_code,
            [200, 302]
        )

        reservation.refresh_from_db()

        self.assertEqual(
            reservation.start_time,
            original_start
        )

        self.assertEqual(
            reservation.end_time,
            original_end
        )

        self.assertEqual(
            reservation.status,
            'approved'
        )

        self.assertFalse(
            ReservationChange.objects.filter(
                reservation=reservation,
                new_start_time=self.make_datetime(13),
                new_end_time=self.make_datetime(15)
            ).exists()
        )

    def test_basic_user_cannot_reschedule_reservation(self):

        reservation = self.make_reservation(
            status='approved'
        )

        self.client.force_login(
            self.basic_user
        )

        response = self.client.post(
            reverse(
                'reschedule_reservation',
                args=[reservation.pk]
            ),
            {
                'start_time': self.make_datetime(13).strftime(
                    '%Y-%m-%dT%H:%M'
                ),
                'end_time': self.make_datetime(15).strftime(
                    '%Y-%m-%dT%H:%M'
                ),
                'reason': 'Unauthorized rescheduling'
            }
        )

        self.assertEqual(
            response.status_code,
            403
        )

        reservation.refresh_from_db()

        self.assertEqual(
            reservation.start_time,
            self.start_time
        )

        self.assertEqual(
            reservation.end_time,
            self.end_time
        )

from datetime import time, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from facilities.models import Facility, FacilityCategory
from management.models import AuditLog
from reservations.models import (
    Reservation,
    ReservationChange,
    EventRecord,
    EventIncident
)


class EventMonitoringTests(TestCase):

    def setUp(self):

        User = get_user_model()

        self.basic_user = User.objects.create_user(
            username='eventuser',
            email='eventuser@example.com',
            password='TestPassword123!'
        )

        self.admin_user = User.objects.create_user(
            username='eventadmin',
            email='eventadmin@example.com',
            password='AdminPassword123!',
            is_staff=True
        )

        self.category = FacilityCategory.objects.create(
            name='Event Testing Facilities',
            is_active=True
        )

        self.facility = Facility.objects.create(
            category=self.category,
            code='EVENT-TEST-001',
            name='Event Testing Room',
            location='Main Building',
            capacity=100,
            opening_time=time(8, 0),
            closing_time=time(17, 0),
            is_active=True
        )

    def make_reservation(
        self,
        status='approved',
        start_time=None,
        end_time=None
    ):

        now = timezone.now()

        if start_time is None:
            start_time = now - timedelta(minutes=30)

        if end_time is None:
            end_time = now + timedelta(minutes=30)

        return Reservation.objects.create(
            user=self.basic_user,
            facility=self.facility,
            event_title='Event Monitoring Test',
            purpose='Testing event monitoring',
            participant_count=30,
            start_time=start_time,
            end_time=end_time,
            status=status
        )

    def admin_action(self, reservation, action, reason=''):

        self.client.force_login(self.admin_user)

        return self.client.post(
            reverse(
                'update_reservation_status',
                args=[reservation.pk]
            ),
            {
                'action': action,
                'reason': reason
            }
        )

    def test_admin_can_check_in_approved_reservation(self):

        reservation = self.make_reservation()

        response = self.admin_action(
            reservation,
            'CHECK_IN'
        )

        self.assertEqual(response.status_code, 302)

        reservation.refresh_from_db()

        self.assertEqual(
            reservation.status,
            'checked_in'
        )

        event_record = EventRecord.objects.get(
            reservation=reservation
        )

        self.assertIsNotNone(
            event_record.actual_start
        )

        self.assertEqual(
            event_record.checked_in_by,
            self.admin_user
        )

        self.assertTrue(
            ReservationChange.objects.filter(
                reservation=reservation,
                previous_status='approved',
                new_status='checked_in',
                changed_by=self.admin_user
            ).exists()
        )

        self.assertTrue(
            AuditLog.objects.filter(
                admin_user=self.admin_user,
                action='CHECK_IN'
            ).exists()
        )

    def test_check_in_before_start_is_prevented(self):

        now = timezone.now()

        reservation = self.make_reservation(
            start_time=now + timedelta(hours=1),
            end_time=now + timedelta(hours=2)
        )

        response = self.admin_action(
            reservation,
            'CHECK_IN'
        )

        self.assertEqual(response.status_code, 302)

        reservation.refresh_from_db()

        self.assertEqual(
            reservation.status,
            'approved'
        )

        self.assertFalse(
            EventRecord.objects.filter(
                reservation=reservation
            ).exists()
        )

    def test_check_in_after_end_is_prevented(self):

        now = timezone.now()

        reservation = self.make_reservation(
            start_time=now - timedelta(hours=3),
            end_time=now - timedelta(hours=1)
        )

        response = self.admin_action(
            reservation,
            'CHECK_IN'
        )

        self.assertEqual(response.status_code, 302)

        reservation.refresh_from_db()

        self.assertEqual(
            reservation.status,
            'approved'
        )

        self.assertFalse(
            EventRecord.objects.filter(
                reservation=reservation
            ).exists()
        )

    def test_admin_can_complete_checked_in_event(self):

        reservation = self.make_reservation(
            status='checked_in'
        )

        EventRecord.objects.create(
            reservation=reservation,
            actual_start=timezone.now() - timedelta(minutes=20),
            checked_in_by=self.admin_user
        )

        response = self.admin_action(
            reservation,
            'COMPLETE'
        )

        self.assertEqual(response.status_code, 302)

        reservation.refresh_from_db()

        self.assertEqual(
            reservation.status,
            'completed'
        )

        event_record = EventRecord.objects.get(
            reservation=reservation
        )

        self.assertIsNotNone(
            event_record.actual_end
        )

        self.assertEqual(
            event_record.completed_by,
            self.admin_user
        )

        self.assertTrue(
            ReservationChange.objects.filter(
                reservation=reservation,
                previous_status='checked_in',
                new_status='completed'
            ).exists()
        )

        self.assertTrue(
            AuditLog.objects.filter(
                admin_user=self.admin_user,
                action='COMPLETE'
            ).exists()
        )

    def test_event_cannot_be_completed_without_check_in(self):

        reservation = self.make_reservation(
            status='approved'
        )

        response = self.admin_action(
            reservation,
            'COMPLETE'
        )

        self.assertEqual(response.status_code, 302)

        reservation.refresh_from_db()

        self.assertEqual(
            reservation.status,
            'approved'
        )

        self.assertFalse(
            EventRecord.objects.filter(
                reservation=reservation
            ).exists()
        )

    def test_admin_can_mark_no_show_after_end(self):

        now = timezone.now()

        reservation = self.make_reservation(
            start_time=now - timedelta(hours=3),
            end_time=now - timedelta(hours=1)
        )

        response = self.admin_action(
            reservation,
            'NO_SHOW'
        )

        self.assertEqual(response.status_code, 302)

        reservation.refresh_from_db()

        self.assertEqual(
            reservation.status,
            'no_show'
        )

        event_record = EventRecord.objects.get(
            reservation=reservation
        )

        self.assertIsNotNone(
            event_record.no_show_at
        )

        self.assertEqual(
            event_record.no_show_marked_by,
            self.admin_user
        )

        self.assertTrue(
            ReservationChange.objects.filter(
                reservation=reservation,
                previous_status='approved',
                new_status='no_show'
            ).exists()
        )

        self.assertTrue(
            AuditLog.objects.filter(
                admin_user=self.admin_user,
                action='NO_SHOW'
            ).exists()
        )

    def test_no_show_before_end_is_prevented(self):

        now = timezone.now()

        reservation = self.make_reservation(
            start_time=now + timedelta(hours=1),
            end_time=now + timedelta(hours=2)
        )

        response = self.admin_action(
            reservation,
            'NO_SHOW'
        )

        self.assertEqual(response.status_code, 302)

        reservation.refresh_from_db()

        self.assertEqual(
            reservation.status,
            'approved'
        )

        self.assertFalse(
            EventRecord.objects.filter(
                reservation=reservation
            ).exists()
        )

    def test_checked_in_event_cannot_be_marked_no_show(self):

        reservation = self.make_reservation(
            status='checked_in'
        )

        event_record = EventRecord.objects.create(
            reservation=reservation,
            actual_start=timezone.now(),
            checked_in_by=self.admin_user
        )

        response = self.admin_action(
            reservation,
            'NO_SHOW'
        )

        self.assertEqual(response.status_code, 302)

        reservation.refresh_from_db()
        event_record.refresh_from_db()

        self.assertEqual(
            reservation.status,
            'checked_in'
        )

        self.assertIsNone(
            event_record.no_show_at
        )

    def test_admin_can_submit_incident_report(self):

        reservation = self.make_reservation(
            status='checked_in'
        )

        event_record = EventRecord.objects.create(
            reservation=reservation,
            actual_start=timezone.now(),
            checked_in_by=self.admin_user
        )

        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse(
                'report_event_incident',
                args=[reservation.pk]
            ),
            {
                'description': 'Projector stopped working during the event.'
            }
        )

        self.assertEqual(response.status_code, 302)

        incident = EventIncident.objects.get(
            event_record=event_record
        )

        self.assertEqual(
            incident.description,
            'Projector stopped working during the event.'
        )

        self.assertEqual(
            incident.reported_by,
            self.admin_user
        )

        self.assertTrue(
            AuditLog.objects.filter(
                admin_user=self.admin_user,
                action='CREATE',
                description__icontains='Incident recorded'
            ).exists()
        )

    def test_incident_cannot_be_reported_for_pending_reservation(self):

        reservation = self.make_reservation(
            status='pending'
        )

        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse(
                'report_event_incident',
                args=[reservation.pk]
            ),
            {
                'description': 'Invalid incident report'
            }
        )

        self.assertEqual(response.status_code, 302)

        self.assertFalse(
            EventIncident.objects.exists()
        )

    def test_empty_incident_description_is_rejected(self):

        reservation = self.make_reservation(
            status='checked_in'
        )

        EventRecord.objects.create(
            reservation=reservation,
            actual_start=timezone.now(),
            checked_in_by=self.admin_user
        )

        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse(
                'report_event_incident',
                args=[reservation.pk]
            ),
            {
                'description': '   '
            }
        )

        self.assertEqual(response.status_code, 302)

        self.assertFalse(
            EventIncident.objects.exists()
        )

    def test_basic_user_cannot_check_in_reservation(self):

        reservation = self.make_reservation()

        self.client.force_login(self.basic_user)

        response = self.client.post(
            reverse(
                'update_reservation_status',
                args=[reservation.pk]
            ),
            {
                'action': 'CHECK_IN'
            }
        )

        self.assertEqual(response.status_code, 403)

        reservation.refresh_from_db()

        self.assertEqual(
            reservation.status,
            'approved'
        )

        self.assertFalse(
            EventRecord.objects.filter(
                reservation=reservation
            ).exists()
        )

    def test_basic_user_cannot_submit_incident_report(self):

        reservation = self.make_reservation(
            status='checked_in'
        )

        EventRecord.objects.create(
            reservation=reservation,
            actual_start=timezone.now(),
            checked_in_by=self.admin_user
        )

        self.client.force_login(self.basic_user)

        response = self.client.post(
            reverse(
                'report_event_incident',
                args=[reservation.pk]
            ),
            {
                'description': 'Unauthorized incident report'
            }
        )

        self.assertEqual(response.status_code, 403)

        self.assertFalse(
            EventIncident.objects.exists()
        )

    def test_admin_can_access_approved_event_slip(self):

        reservation = self.make_reservation(
            status='approved'
        )

        self.client.force_login(self.admin_user)

        response = self.client.get(
            reverse(
                'printable_event_slip',
                args=[reservation.pk]
            )
        )

        self.assertEqual(response.status_code, 200)