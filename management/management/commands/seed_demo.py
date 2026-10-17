
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

CATEGORY_DATA = [
    (
        "IT401W Demo Classrooms",
        "Lecture Rooms",
        "Rooms for lectures, seminars, and class activities.",
    ),
    (
        "IT401W Demo Laboratories",
        "Laboratories",
        "Specialized rooms for hands-on academic activities.",
    ),
    (
        "IT401W Demo Event Venues",
        "Event and Meeting Spaces",
        "Venues for meetings, conferences, and campus events.",
    ),
]

AMENITY_DATA = [
    ("IT401W Demo Wi-Fi", "Wi-Fi Access"),
    ("IT401W Demo Projector", "LCD Projector"),
    ("IT401W Demo Air Conditioning", "Air Conditioning"),
    ("IT401W Demo Sound System", "Sound System"),
    ("IT401W Demo Whiteboard", "Whiteboard"),
    ("IT401W Demo Microphones", "Wireless Microphones"),
    ("IT401W Demo Computers", "Desktop Computers"),
    ("IT401W Demo Accessible Entrance", "Accessible Entrance"),
]

FACILITY_DATA = [
    (
        "DEMO-FAC-01", "LR-A101", "Lecture Room A101",
        "Academic Building A, 1st Floor", 40, 0,
    ),
    (
        "DEMO-FAC-02", "LR-A102", "Lecture Room A102",
        "Academic Building A, 1st Floor", 45, 0,
    ),
    (
        "DEMO-FAC-03", "LAB-B201", "Computer Laboratory B201",
        "Technology Building B, 2nd Floor", 35, 1,
    ),
    (
        "DEMO-FAC-04", "LAB-B202", "Science Laboratory B202",
        "Science Building B, 2nd Floor", 30, 1,
    ),
    (
        "DEMO-FAC-05", "EVT-SC01", "University Multipurpose Hall",
        "Student Center, Ground Floor", 150, 2,
    ),
    (
        "DEMO-FAC-06", "MTG-C301", "Conference Room C301",
        "Administration Building C, 3rd Floor", 60, 2,
    ),
]

USER_DATA = [
    ("Miguel", "Santos", "miguel.santos"),
    ("Andrea", "Reyes", "andrea.reyes"),
    ("Joshua", "Cruz", "joshua.cruz"),
    ("Sofia", "Garcia", "sofia.garcia"),
    ("Daniel", "Mendoza", "daniel.mendoza"),
    ("Isabella", "Torres", "isabella.torres"),
    ("Nathan", "Flores", "nathan.flores"),
    ("Camille", "Ramos", "camille.ramos"),
]

EVENT_TITLES = [
    "College Orientation Program",
    "Student Research Symposium",
    "Faculty Curriculum Workshop",
    "Campus Safety Seminar",
    "Student Leadership Training",
    "Digital Literacy Workshop",
    "Research Proposal Consultation",
    "Academic Advising Session",
    "Information Technology Colloquium",
    "Web Development Seminar",
    "Computer Laboratory Training",
    "Cybersecurity Awareness Forum",
    "Science Laboratory Orientation",
    "University Organization Assembly",
    "Department Planning Meeting",
    "Student Council Consultation",
    "Thesis Writing Workshop",
    "Faculty Coordination Meeting",
    "Career Preparation Seminar",
    "Programming Skills Workshop",
    "Student Organization Planning",
    "Laboratory Equipment Briefing",
    "Peer Mentoring Session",
    "Community Outreach Planning",
]

CLOSURE_REASONS = [
    "Air-conditioning inspection",
    "Electrical system maintenance",
    "Computer workstation servicing",
    "Laboratory safety inspection",
    "Audio equipment maintenance",
]


def local_datetime(day, hour, minute=0):
    return timezone.make_aware(
        datetime.combine(day, time(hour, minute)),
        MANILA,
    )


class Command(BaseCommand):
    help = "Create or refresh fictional campus reservation sample records."

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

    def rename_or_create(self, model, old_lookup, new_lookup, fields):
        """
        Rename existing seeded records without changing their primary keys.
        This preserves their existing relationships.
        """
        old = model.objects.filter(**old_lookup).first()
        new = model.objects.filter(**new_lookup).first()

        if old is not None and new is not None and old.pk != new.pk:

            if model is Amenity:
                # Transfer facilities to the existing realistic amenity.
                for facility in Facility.objects.filter(amenities=old):
                    facility.amenities.add(new)

                # Remove only the old sample amenity.
                old.delete()
                obj = new

            elif model is FacilityCategory:
                # Keep facilities connected to the existing category.
                Facility.objects.filter(category=old).update(
                    category=new
                )

                old.delete()
                obj = new

            else:
                raise CommandError(
                    f"Both old and new records exist in "
                    f"{model.__name__}: {old_lookup} / {new_lookup}."
                )

        else:
            obj = old or new
        created = obj is None

        if created:
            obj = model.objects.create(**new_lookup, **fields)
        else:
            for key, value in {**new_lookup, **fields}.items():
                setattr(obj, key, value)

            obj.save(
                update_fields=list({**new_lookup, **fields})
            )

        return obj, created

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()

        # CATEGORIES
        categories = []

        for old_name, new_name, description in CATEGORY_DATA:
            category, _ = self.rename_or_create(
                FacilityCategory,
                {"name": old_name},
                {"name": new_name},
                {
                    "description": description,
                    "is_active": True,
                },
            )
            categories.append(category)

        # AMENITIES
        amenities = []

        for old_name, new_name in AMENITY_DATA:
            amenity, _ = self.rename_or_create(
                Amenity,
                {"name": old_name},
                {"name": new_name},
                {
                    "description": (
                        f"Available facility equipment: {new_name}."
                    ),
                    "is_active": True,
                },
            )
            amenities.append(amenity)

        # FACILITIES
        facilities = []

        for index, details in enumerate(FACILITY_DATA):
            (
                old_code,
                code,
                name,
                location,
                capacity,
                category_index,
            ) = details

            facility, created = self.rename_or_create(
                Facility,
                {"code": old_code},
                {"code": code},
                {
                    "name": name,
                    "location": location,
                    "category": categories[category_index],
                    "capacity": capacity,
                    "description": (
                        "Campus facility available for approved "
                        f"academic activities: {name}."
                    ),
                    "opening_time": time(8, 0),
                    "closing_time": time(17, 0),
                    "is_active": True,
                },
            )

            if created:
                facility.amenities.set([
                    amenities[(index + shift) % len(amenities)]
                    for shift in range(3)
                ])

            facilities.append(facility)

        # ACCOUNT PASSWORDS
        password = None

        def password_for_new_account():
            nonlocal password

            if password is None:
                password = getpass(
                    "Choose a password for newly created "
                    "sample accounts (12+ characters): "
                )

                if len(password) < 12:
                    raise CommandError(
                        "Use a password with at least 12 characters."
                    )

            return password

        # RENAME EXISTING ACCOUNTS OR CREATE MISSING ACCOUNTS
        def account(
            old_usernames,
            username,
            first_name,
            last_name,
            is_admin,
        ):
            existing_new = User.objects.filter(
                username=username
            ).first()

            existing_old = list(
                User.objects.filter(username__in=old_usernames)
            )

            if len(existing_old) > 1:
                raise CommandError(
                    f"Multiple previous accounts found for "
                    f"{username}; resolve manually."
                )

            old = existing_old[0] if existing_old else None

            if old and existing_new and old.pk != existing_new.pk:
                raise CommandError(
                    f"Both previous and new usernames exist "
                    f"for {username}; resolve manually."
                )

            user = old or existing_new

            if user is None:
                user = User(
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    is_staff=is_admin,
                    is_superuser=False,
                    is_active=True,
                )
                user.set_password(password_for_new_account())
                user.save()

            else:
                if is_admin and (
                    not user.is_staff or not user.is_active
                ):
                    raise CommandError(
                        f"Existing {username} is not an active admin."
                    )

                if not is_admin and (
                    user.is_staff or user.is_superuser
                ):
                    raise CommandError(
                        f"Existing {username} has admin privileges."
                    )

                user.username = username
                user.first_name = first_name
                user.last_name = last_name

                user.save(
                    update_fields=[
                        "username",
                        "first_name",
                        "last_name",
                    ]
                )

            return user

        # ADMIN ACCOUNTS
        admin = account(
            ["demo_admin"],
            "admin_adrian",
            "Admin Adrian",
            "Reyes",
            True,
        )

        account(
            ["admin_mischa"],
            "admin_sofia",
            "Admin Sofia",
            "Mendoza",
            True,
        )

        # BASIC USER ACCOUNTS
        users = []

        for number, details in enumerate(USER_DATA, start=1):
            first, last, username = details

            user = account(
                [f"demo_user_{number:02d}"],
                username,
                first,
                last,
                False,
            )
            users.append(user)

        # RENAME EXISTING RESERVATION EVENTS
        # Keep their IDs, users, statuses, and history unchanged.
        for number, title in enumerate(EVENT_TITLES, start=1):
            old_title = f"IT401W Demo Event {number:02d}"

            old_records = Reservation.objects.filter(
                event_title=old_title
            )
            new_records = Reservation.objects.filter(
                event_title=title
            )

            if (
                old_records.count() > 1
                or new_records.count() > 1
            ):
                raise CommandError(
                    f"Multiple reservations share the sample "
                    f"event title: {title}."
                )

            if old_records.exists() and new_records.exists():
                raise CommandError(
                    f"Both old and new event titles exist for {title}."
                )

            if old_records.exists():
                old_records.update(event_title=title)

            Reservation.objects.filter(
                event_title=title,
                purpose="Fictional completed or missed campus event.",
            ).update(
                purpose=f"Academic activity: {title}."
            )

            Reservation.objects.filter(
                event_title=title,
                purpose="Fictional campus activity for testing.",
            ).update(
                purpose=f"Academic activity: {title}."
            )

            Reservation.objects.filter(
                event_title=title,
                decision_reason="Approved for historical demonstration.",
            ).update(
                decision_reason="Approved by the campus facilities office."
            )

            Reservation.objects.filter(
                event_title=title,
                decision_reason=(
                    "Fictional request rejected for demonstration."
                ),
            ).update(
                decision_reason=(
                    "Request did not meet facility scheduling requirements."
                )
            )

            Reservation.objects.filter(
                event_title=title,
                decision_reason=(
                    "Fictional request approved for demonstration."
                ),
            ).update(
                decision_reason="Approved by the campus facilities office."
            )

        today = timezone.localdate(timezone=MANILA)

        # HISTORICAL RESERVATIONS
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
            title = EVENT_TITLES[index]
            user = users[index]
            facility = facilities[index % 6]

            start = local_datetime(
                today - timedelta(days=15 + index),
                9,
            )
            end = start + timedelta(hours=1)

            if Reservation.objects.filter(
                user=user,
                event_title=title,
            ).exists():
                continue

            created_at = start - timedelta(days=2)
            approved_at = start - timedelta(days=1)

            reservation = Reservation.objects.create(
                user=user,
                facility=facility,
                event_title=title,
                purpose=f"Academic activity: {title}.",
                participant_count=15,
                start_time=start,
                end_time=end,
                status=final_status,
                decision_by=admin,
                decision_at=approved_at,
                decision_reason=(
                    "Approved by the campus facilities office."
                ),
            )

            Reservation.objects.filter(
                pk=reservation.pk
            ).update(created_at=created_at)

            self.add_history(
                reservation,
                user,
                "",
                "pending",
                created_at,
                "Initial request.",
            )

            self.add_history(
                reservation,
                admin,
                "pending",
                "approved",
                approved_at,
                "Request approved.",
            )

            self.add_audit(
                admin,
                "APPROVE",
                "Reservation",
                reservation,
                "Reservation approved.",
                approved_at,
            )

            if final_status == "completed":
                self.add_history(
                    reservation,
                    admin,
                    "approved",
                    "checked_in",
                    start,
                    "Attendee checked in.",
                )

                self.add_history(
                    reservation,
                    admin,
                    "checked_in",
                    "completed",
                    end,
                    "Event completed.",
                )

                self.add_audit(
                    admin,
                    "CHECK_IN",
                    "Reservation",
                    reservation,
                    "Event check-in recorded.",
                    start,
                )

                self.add_audit(
                    admin,
                    "COMPLETE",
                    "Reservation",
                    reservation,
                    "Event completion recorded.",
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
                            "Minor equipment issue resolved "
                            "during the event."
                        ),
                        reported_by=admin,
                    )

            else:
                no_show_time = end + timedelta(minutes=15)

                self.add_history(
                    reservation,
                    admin,
                    "approved",
                    "no_show",
                    no_show_time,
                    "Organizer did not check in.",
                )

                self.add_audit(
                    admin,
                    "NO_SHOW",
                    "Reservation",
                    reservation,
                    "No-show recorded.",
                    no_show_time,
                )

                EventRecord.objects.create(
                    reservation=reservation,
                    no_show_at=no_show_time,
                    no_show_marked_by=admin,
                )

        # FUTURE RESERVATIONS
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

            title = EVENT_TITLES[index + 8]
            user = users[index % 8]
            facility = facilities[facility_index]

            start = local_datetime(future_day, start_hour)
            end = start + timedelta(hours=1)

            if Reservation.objects.filter(
                user=user,
                event_title=title,
            ).exists():
                continue

            reservation = Reservation(
                user=user,
                facility=facility,
                event_title=title,
                purpose=f"Academic activity: {title}.",
                participant_count=15,
                start_time=start,
                end_time=end,
                status="pending",
            )

            reservation.full_clean()
            reservation.save()

            self.add_history(
                reservation,
                user,
                "",
                "pending",
                reservation.created_at,
                "Initial request.",
            )

            if final_status == "pending":
                continue

            reservation.status = final_status

            if final_status in ["approved", "rejected"]:
                reservation.decision_by = admin
                reservation.decision_at = timezone.now()

                if final_status == "rejected":
                    reservation.decision_reason = (
                        "Request did not meet facility "
                        "scheduling requirements."
                    )
                else:
                    reservation.decision_reason = (
                        "Approved by the campus facilities office."
                    )

            reservation.full_clean()
            reservation.save()

            self.add_history(
                reservation,
                admin,
                "pending",
                final_status,
                timezone.now(),
                "Reservation status updated.",
            )

            action = {
                "approved": "APPROVE",
                "rejected": "REJECT",
                "cancelled": "CANCEL",
            }[final_status]

            self.add_audit(
                admin,
                action,
                "Reservation",
                reservation,
                f"Reservation marked {final_status}.",
                timezone.now(),
            )

        # FACILITY MAINTENANCE CLOSURES
        for index, reason in enumerate(CLOSURE_REASONS):
            facility = facilities[index]
            old_reason = f"IT401W demo maintenance {index + 1}"

            old_closures = FacilityClosure.objects.filter(
                facility=facility,
                reason=old_reason,
            )
            new_closures = FacilityClosure.objects.filter(
                facility=facility,
                reason=reason,
            )

            if old_closures.exists() and new_closures.exists():
                raise CommandError(
                    f"Both old and new maintenance records "
                    f"exist for {facility.name}."
                )

            if old_closures.exists():
                old_closures.update(
                    reason=reason,
                    created_by=admin
                )
                continue

            if new_closures.exists():
                new_closures.filter(
                    created_by__isnull=True
                ).update(created_by=admin)
                continue

            closure_day = today + timedelta(days=45 + index)

            closure = FacilityClosure(
                facility=facility,
                start_time=local_datetime(closure_day, 13),
                end_time=local_datetime(closure_day, 15),
                reason=reason,
                is_active=True,
                created_by=admin,
            )

            closure.full_clean()
            closure.save()

            self.add_audit(
                admin,
                "CREATE",
                "FacilityClosure",
                closure,
                "Maintenance closure scheduled.",
                timezone.now(),
            )

        # UPDATE LEGACY AUDIT AND HISTORY DESCRIPTIONS
        AuditLog.objects.filter(
            description="Approved fictional request."
        ).update(
            description="Reservation approved."
        )

        AuditLog.objects.filter(
            description="Fictional maintenance closure created."
        ).update(
            description="Maintenance closure scheduled."
        )

        for status in ["approved", "rejected", "cancelled"]:
            AuditLog.objects.filter(
                description=f"Fictional reservation marked {status}."
            ).update(
                description=f"Reservation marked {status}."
            )

        ReservationChange.objects.filter(
            reason="Demonstration status transition."
        ).update(
            reason="Reservation status updated."
        )

        EventIncident.objects.filter(
            description=(
                "Fictional minor equipment issue "
                "resolved during the event."
            )
        ).update(
            description=(
                "Minor equipment issue resolved during the event."
            )
        )

        # CHECK OVERLAPPING RESERVATIONS
        first_approved = Reservation.objects.get(
            event_title=EVENT_TITLES[8],
            user=users[0],
        )

        if first_approved.start_time > timezone.now():
            conflict = Reservation(
                user=users[1],
                facility=first_approved.facility,
                event_title="Unsaved Conflict Test",
                purpose="Verify overlapping reservation rejection.",
                participant_count=10,
                start_time=first_approved.start_time,
                end_time=first_approved.end_time,
                status="approved",
            )

            try:
                conflict.full_clean()

            except ValidationError as error:
                messages = error.message_dict.get(
                    "start_time", []
                )

                if not any(
                    "already has an approved" in message
                    for message in messages
                ):
                    raise CommandError(
                        "Conflict test failed for an unexpected reason."
                    )

            else:
                raise CommandError(
                    "Conflict test failed: "
                    "overlapping approval was allowed."
                )

            self.stdout.write(
                self.style.SUCCESS(
                    "Conflict test passed: "
                    "overlapping approval rejected."
                )
            )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Sample database updated successfully."
            )
        )
        self.stdout.write(
            "ADMIN: admin_adrian / admin_sofia"
        )
        self.stdout.write(
            "BASIC USERS: 8 fictional name-based accounts"
        )
        self.stdout.write(
            "Existing passwords and linked records were preserved."
        )
