
from datetime import datetime, time, timedelta
from getpass import getpass
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from facilities.models import (
    Amenity,
    Facility,
    FacilityCategory,
    FacilityClosure,
)
from management.models import AuditLog
from reservations.models import (
    EventIncident,
    EventRecord,
    Reservation,
    ReservationChange,
)


MANILA = ZoneInfo("Asia/Manila")


def local_datetime(day, hour, minute=0):
    return timezone.make_aware(
        datetime.combine(day, time(hour, minute)),
        MANILA,
    )


class Command(BaseCommand):
    help = "Create repeatable fictional demonstration data."

    def add_history(self, reservation, actor, old, new, when, reason):
        record = ReservationChange.objects.create(
            reservation=reservation,
            changed_by=actor,
            previous_status=old,
            new_status=new,
            previous_start_time=reservation.start_time,
            previous_end_time=reservation.end_time,
            new_start_time=reservation.start_time,
            new_end_time=reservation.end_time,
            reason=reason,
        )

        ReservationChange.objects.filter(
            pk=record.pk
        ).update(changed_at=when)

    def add_audit(self, admin, action, model_name, obj, description, when):
        record = AuditLog.objects.create(
            admin_user=admin,
            action=action,
            model_name=model_name,
            object_id=obj.pk,
            description=description,
        )

        AuditLog.objects.filter(
            pk=record.pk
        ).update(timestamp=when)

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()

        category_names = [
            "IT401W Demo Classrooms",
            "IT401W Demo Laboratories",
            "IT401W Demo Event Venues",
        ]

        categories = []

        for name in category_names:
            category, _ = FacilityCategory.objects.get_or_create(
                name=name,
                defaults={
                    "description": "Fictional demonstration category.",
                    "is_active": True,
                },
            )
            categories.append(category)

        amenity_names = [
            "IT401W Demo Wi-Fi",
            "IT401W Demo Projector",
            "IT401W Demo Air Conditioning",
            "IT401W Demo Sound System",
            "IT401W Demo Whiteboard",
            "IT401W Demo Microphones",
            "IT401W Demo Computers",
            "IT401W Demo Accessible Entrance",
        ]

        amenities = []

        for name in amenity_names:
            amenity, _ = Amenity.objects.get_or_create(
                name=name,
                defaults={
                    "description": "Fictional demonstration amenity.",
                    "is_active": True,
                },
            )
            amenities.append(amenity)

        facility_details = [
            ("DEMO-FAC-01", "Demo Lecture Room 101", "Building A", 40, 0),
            ("DEMO-FAC-02", "Demo Lecture Room 102", "Building A", 45, 0),
            ("DEMO-FAC-03", "Demo Computer Laboratory", "Building B", 35, 1),
            ("DEMO-FAC-04", "Demo Science Laboratory", "Building B", 30, 1),
            ("DEMO-FAC-05", "Demo Multipurpose Hall", "Student Center", 150, 2),
            ("DEMO-FAC-06", "Demo Conference Room", "Building C", 60, 2),
        ]

        facilities = []

        for index, details in enumerate(facility_details):
            code, name, location, capacity, category_index = details

            facility, created = Facility.objects.get_or_create(
                code=code,
                defaults={
                    "category": categories[category_index],
                    "name": name,
                    "location": location,
                    "capacity": capacity,
                    "description": "Fictional facility for testing.",
                    "opening_time": time(8, 0),
                    "closing_time": time(17, 0),
                    "is_active": True,
                },
            )

            if created:
                facility.amenities.set([
                    amenities[index % 8],
                    amenities[(index + 1) % 8],
                    amenities[(index + 2) % 8],
                ])

            facilities.append(facility)

        usernames = ["demo_admin"] + [
            f"demo_user_{number:02d}"
            for number in range(1, 9)
        ]

        missing_accounts = [
            username
            for username in usernames
            if not User.objects.filter(username=username).exists()
        ]

        password = None

        if missing_accounts:
            password = getpass(
                "Choose a password for new fictional demo authentication: "
            )

            if len(password) < 12:
                raise CommandError(
                    "Use a demo password with at least 12 characters."
                )

        admin, _ = User.objects.get_or_create(
            username="demo_admin",
            defaults={
                "first_name": "Demo",
                "last_name": "Administrator",
                "is_staff": True,
                "is_superuser": False,
                "is_active": True,
            },
        )

        if not admin.is_staff or not admin.is_active:
            raise CommandError(
                "demo_admin already exists but is not an active admin."
            )

        if "demo_admin" in missing_accounts:
            admin.set_password(password)
            admin.save(update_fields=["password"])

        users = []

        for number in range(1, 9):
            username = f"demo_user_{number:02d}"

            user, _ = User.objects.get_or_create(
                username=username,
                defaults={
                    "first_name": f"Demo {number}",
                    "last_name": "Student",
                    "is_staff": False,
                    "is_superuser": False,
                    "is_active": True,
                },
            )

            if user.is_staff or user.is_superuser:
                raise CommandError(
                    f"{username} already exists with admin privileges."
                )

            if username in missing_accounts:
                user.set_password(password)
                user.save(update_fields=["password"])

            users.append(user)

        today = timezone.localdate(timezone=MANILA)

        historical_statuses = [
            "completed",
            "completed",
            "completed",
            "completed",
            "completed",
            "no_show",
            "no_show",
            "no_show",
        ]

        for index, final_status in enumerate(historical_statuses):
            event_number = index + 1
            event_title = f"IT401W Demo Event {event_number:02d}"
            user = users[index]
            facility = facilities[index % 6]
            event_day = today - timedelta(days=15 + index)

            start = local_datetime(event_day, 9)
            end = local_datetime(event_day, 10)

            if Reservation.objects.filter(
                user=user,
                event_title=event_title,
            ).exists():
                continue

            created_at = start - timedelta(days=2)
            approved_at = start - timedelta(days=1)

            reservation = Reservation.objects.create(
                user=user,
                facility=facility,
                event_title=event_title,
                purpose="Fictional completed or missed campus event.",
                participant_count=15,
                start_time=start,
                end_time=end,
                status=final_status,
                decision_by=admin,
                decision_at=approved_at,
                decision_reason="Approved for historical demonstration.",
            )

            Reservation.objects.filter(
                pk=reservation.pk
            ).update(created_at=created_at)

            self.add_history(
                reservation, user, "", "pending",
                created_at, "Initial request.",
            )

            self.add_history(
                reservation, admin, "pending", "approved",
                approved_at, "Request approved.",
            )

            self.add_audit(
                admin, "APPROVE", "Reservation",
                reservation, "Approved fictional request.",
                approved_at,
            )

            if final_status == "completed":
                self.add_history(
                    reservation, admin, "approved", "checked_in",
                    start, "Attendee checked in.",
                )

                self.add_history(
                    reservation, admin, "checked_in", "completed",
                    end, "Event completed.",
                )

                self.add_audit(
                    admin, "CHECK_IN", "Reservation",
                    reservation, "Event check-in recorded.",
                    start,
                )

                self.add_audit(
                    admin, "COMPLETE", "Reservation",
                    reservation, "Event completion recorded.",
                    end,
                )

                event_record = EventRecord.objects.create(
                    reservation=reservation,
                    actual_start=start,
                    actual_end=end,
                    checked_in_by=admin,
                    completed_by=admin,
                )

                if index < 2:
                    EventIncident.objects.create(
                        event_record=event_record,
                        description=(
                            "Fictional minor equipment issue "
                            "resolved during the event."
                        ),
                        reported_by=admin,
                    )

            else:
                no_show_time = end + timedelta(minutes=15)

                self.add_history(
                    reservation, admin, "approved", "no_show",
                    no_show_time, "Organizer did not check in.",
                )

                self.add_audit(
                    admin, "NO_SHOW", "Reservation",
                    reservation, "No-show recorded.",
                    no_show_time,
                )

                EventRecord.objects.create(
                    reservation=reservation,
                    no_show_at=no_show_time,
                    no_show_marked_by=admin,
                )

        future_details = [
            (0, 9, "approved"),
            (0, 10, "approved"),
            (1, 9, "approved"),
            (2, 9, "approved"),
            (3, 9, "approved"),
            (4, 9, "approved"),
            (5, 9, "pending"),
            (1, 10, "pending"),
            (2, 10, "pending"),
            (3, 10, "pending"),
            (4, 10, "pending"),
            (0, 11, "rejected"),
            (1, 11, "rejected"),
            (2, 11, "rejected"),
            (3, 11, "cancelled"),
            (4, 11, "cancelled"),
        ]

        future_day = today + timedelta(days=1)

        for index, details in enumerate(future_details):
            facility_index, start_hour, final_status = details

            event_number = index + 9
            event_title = f"IT401W Demo Event {event_number:02d}"
            user = users[index % 8]
            facility = facilities[facility_index]

            start = local_datetime(future_day, start_hour)
            end = start + timedelta(hours=1)

            if Reservation.objects.filter(
                user=user,
                event_title=event_title,
            ).exists():
                continue

            reservation = Reservation(
                user=user,
                facility=facility,
                event_title=event_title,
                purpose="Fictional campus activity for testing.",
                participant_count=15,
                start_time=start,
                end_time=end,
                status="pending",
            )

            reservation.full_clean()
            reservation.save()

            self.add_history(
                reservation, user, "", "pending",
                reservation.created_at, "Initial request.",
            )

            if final_status == "pending":
                continue

            reservation.status = final_status

            if final_status in ["approved", "rejected"]:
                reservation.decision_by = admin
                reservation.decision_at = timezone.now()

                if final_status == "rejected":
                    reservation.decision_reason = (
                        "Fictional request rejected for demonstration."
                    )
                else:
                    reservation.decision_reason = (
                        "Fictional request approved for demonstration."
                    )

            reservation.full_clean()
            reservation.save()

            self.add_history(
                reservation, admin, "pending", final_status,
                timezone.now(), "Demonstration status transition.",
            )

            action = {
                "approved": "APPROVE",
                "rejected": "REJECT",
                "cancelled": "CANCEL",
            }[final_status]

            self.add_audit(
                admin, action, "Reservation",
                reservation,
                f"Fictional reservation marked {final_status}.",
                timezone.now(),
            )

        for index in range(5):
            facility = facilities[index]
            reason = f"IT401W demo maintenance {index + 1}"

            if FacilityClosure.objects.filter(
                facility=facility,
                reason=reason,
            ).exists():
                continue

            closure_day = today + timedelta(days=45 + index)

            closure = FacilityClosure(
                facility=facility,
                start_time=local_datetime(closure_day, 13),
                end_time=local_datetime(closure_day, 15),
                reason=reason,
                is_active=True,
            )

            closure.full_clean()
            closure.save()

            self.add_audit(
                admin, "CREATE", "FacilityClosure",
                closure, "Fictional maintenance closure created.",
                timezone.now(),
            )

        first_approved = Reservation.objects.get(
            event_title="IT401W Demo Event 09",
            user=users[0],
        )

        if first_approved.start_time > timezone.now():
            conflict = Reservation(
                user=users[1],
                facility=first_approved.facility,
                event_title="Unsaved Conflict Test",
                purpose="Demonstrate overlapping approval rejection.",
                participant_count=10,
                start_time=first_approved.start_time,
                end_time=first_approved.end_time,
                status="approved",
            )

            try:
                conflict.full_clean()
            except ValidationError as error:
                messages = error.message_dict.get("start_time", [])

                if not any(
                    "already has an approved" in message
                    for message in messages
                ):
                    raise CommandError(
                        "Conflict test failed for an unexpected reason."
                    )
            else:
                raise CommandError(
                    "Conflict test failed: overlapping approval was allowed."
                )

            self.stdout.write(
                self.style.SUCCESS(
                    "Conflict test passed: overlapping approval rejected."
                )
            )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS("Demo database prepared successfully.")
        )
        self.stdout.write(
            "Demo ADMIN: demo_admin"
        )
        self.stdout.write(
            "Demo BASIC USERS: demo_user_01 through demo_user_08"
        )
        self.stdout.write(
            "Passwords are the ones chosen when each account was created."
        )
        self.stdout.write(
            "Existing database records were preserved."
        )
