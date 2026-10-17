from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from django.db.models import Q
from django.shortcuts import render, get_object_or_404
from django.utils import timezone

from management.models import SystemSetting
from reservations.models import Reservation

from .models import (
    Facility,
    FacilityCategory,
    FacilityClosure,
)


MANILA_TZ = ZoneInfo("Asia/Manila")

BLOCKING_STATUSES = [
    "approved",
    "checked_in",
    "completed",
    "no_show",
]


def facility_list(request):

    search_query = request.GET.get("search", "").strip()
    selected_category = request.GET.get("category", "").strip()
    capacity_value = request.GET.get("capacity", "").strip()

    facilities = Facility.objects.filter(
        is_active=True,
        category__is_active=True
    ).select_related(
        "category"
    ).order_by("name")

    # Search by name, location, or facility code
    if search_query:
        facilities = facilities.filter(
            Q(name__icontains=search_query)
            | Q(location__icontains=search_query)
            | Q(code__icontains=search_query)
        )

    # Filter by category
    if selected_category:
        if selected_category.isascii() and selected_category.isdigit() and len(selected_category) <= 9:
            facilities = facilities.filter(
                category_id=int(selected_category)
            )
        else:
            facilities = facilities.none()

    # Filter by minimum participant capacity
    if capacity_value:
        if (
            capacity_value.isascii()
            and capacity_value.isdigit()
            and len(capacity_value) <= 6
            and int(capacity_value) > 0
        ):
            facilities = facilities.filter(
                capacity__gte=int(capacity_value)
            )
        else:
            facilities = facilities.none()

    categories = FacilityCategory.objects.filter(
        is_active=True
    ).order_by("name")

    return render(
        request,
        "facilities/facility_list.html",
        {
            "facilities": facilities,
            "categories": categories,
            "search_query": search_query,
            "selected_category": selected_category,
            "capacity_value": capacity_value,
        }
    )


def facility_detail(request, facility_id):

    facility = get_object_or_404(
        Facility.objects.select_related("category"),
        pk=facility_id,
        is_active=True,
        category__is_active=True
    )

    now = timezone.now()
    today = timezone.localtime(now, MANILA_TZ).date()

    system_setting = SystemSetting.get_current()

    latest_date = today + timedelta(
        days=system_setting.advance_booking_days
    )

    selected_date = today
    date_error = ""

    date_value = request.GET.get("date", "")

    if date_value:
        try:
            selected_date = date.fromisoformat(date_value)
        except (ValueError, TypeError):
            date_error = "Please select a valid date."

    if not date_error:
        if selected_date < today or selected_date > latest_date:
            date_error = (
                "Selected date is outside the allowed "
                "advance-booking window."
            )

    slots = []

    if not date_error:

        day_start = timezone.make_aware(
            datetime.combine(
                selected_date,
                facility.opening_time
            ),
            MANILA_TZ
        )

        day_end = timezone.make_aware(
            datetime.combine(
                selected_date,
                facility.closing_time
            ),
            MANILA_TZ
        )

        if day_end <= day_start:
            date_error = (
                "This facility has invalid operating hours."
            )

        else:

            reservations = Reservation.objects.filter(
                facility=facility,
                status__in=BLOCKING_STATUSES,
                start_time__lt=day_end,
                end_time__gt=day_start
            ).values_list(
                "start_time",
                "end_time"
            )

            closures = FacilityClosure.objects.filter(
                facility=facility,
                is_active=True,
                start_time__lt=day_end,
                end_time__gt=day_start
            ).values_list(
                "start_time",
                "end_time"
            )

            occupied_intervals = (
                list(reservations) + list(closures)
            )

            slot_start = day_start
            slot_length = timedelta(minutes=30)

            while slot_start + slot_length <= day_end:

                slot_end = slot_start + slot_length

                has_conflict = any(
                    slot_start < block_end
                    and slot_end > block_start
                    for block_start, block_end
                    in occupied_intervals
                )

                is_available = (
                    slot_start > now
                    and not has_conflict
                )

                slots.append({
                    "start": slot_start,
                    "end": slot_end,
                    "available": is_available,
                })

                slot_start = slot_end

    amenities = facility.amenities.filter(
        is_active=True
    ).order_by("name")

    return render(
        request,
        "facilities/facility_detail.html",
        {
            "facility": facility,
            "amenities": amenities,
            "slots": slots,
            "today": today,
            "selected_date": selected_date,
            "latest_date": latest_date,
            "date_error": date_error,
            "system_setting": system_setting,
        }
    )
