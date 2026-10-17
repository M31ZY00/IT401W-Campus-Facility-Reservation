from datetime import date, datetime, time, timedelta
import calendar
import csv
from functools import wraps

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import DatabaseError, transaction
from django.db.models import Count, DurationField, ExpressionWrapper, F, Q, Sum
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.db.models.functions import TruncMonth

from facilities.forms import FacilityClosureForm
from facilities.models import Amenity, Facility, FacilityCategory, FacilityClosure
from reservations.models import EventIncident, EventRecord, Reservation, ReservationChange
from reservations.services import reschedule_reservation, update_reservation

from .audit import record_audit
from .forms import AmenityForm, FacilityCategoryForm, FacilityForm
from .models import AuditLog

User = get_user_model()


def admin_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.is_active or not request.user.is_staff:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return wrapper


@admin_required
def admin_dashboard(request):
    current_date = timezone.localdate()
    first_month = current_date.replace(day=1)
    active_statuses = ['approved', 'checked_in', 'completed', 'no_show']


    # Required live dashboard statistics
    cards = {

        # Reservation requests awaiting admin approval
        'pending_reservations': Reservation.objects.filter(
            status='pending'
        ).count(),

        # Approved bookings scheduled in the future
        'upcoming_events': Reservation.objects.filter(
            status='approved',
            start_time__gte=timezone.now()
        ).count(),

        # Reservations marked as completed
        'completed_events': Reservation.objects.filter(
            status='completed'
        ).count(),

        # Facilities that are active and have active categories
        'active_facilities': Facility.objects.filter(
            is_active=True,
            category__is_active=True
        ).count(),

    }

    monthly_query = (
        Reservation.objects.exclude(status__in=['rejected', 'cancelled'])
        .filter(start_time__date__gte=_shift_month(first_month, -5))
        .annotate(month=TruncMonth('start_time', tzinfo=timezone.get_current_timezone()))
        .values('month')
        .annotate(total=Count('id'))
        .order_by('month')
    )
    month_totals = {
        (row['month'].year, row['month'].month): row['total']
        for row in monthly_query
    }
    monthly_rows = []
    for offset in range(-5, 1):
        month = _shift_month(first_month, offset)
        monthly_rows.append({
            'label': month.strftime('%b %Y'),
            'count': month_totals.get((month.year, month.month), 0),
        })
    _add_chart_widths(monthly_rows)

    usage_query = (
        Reservation.objects.filter(status__in=active_statuses)
        .values('facility_id', 'facility__name', 'facility__code')
        .annotate(total=Count('id'))
        .order_by('-total', 'facility__name')[:8]
    )
    facility_rows = [
        {
            'label': f"{row['facility__name']} ({row['facility__code'] or 'No code'})",
            'count': row['total'],
        }
        for row in usage_query
    ]
    _add_chart_widths(facility_rows)

    booked_duration = Reservation.objects.filter(status__in=active_statuses).aggregate(
        total=Sum(ExpressionWrapper(F('end_time') - F('start_time'), output_field=DurationField()))
    )['total'] or timedelta()

    return render(request, 'management/dashboard.html', {
        'cards': cards,
        'monthly_rows': monthly_rows,
        'facility_rows': facility_rows,
        'booked_hours': round(booked_duration.total_seconds() / 3600, 2),
        'completed_events': cards['completed_events'],
    })


@admin_required
def manage_users(request):
    search_query = request.GET.get('search', '').strip()

    users = User.objects.filter(
        is_staff=False,
        is_superuser=False
    ).order_by('username')

    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    return render(request, 'management/manage_users.html', {
        'users': users,
        'search_query': search_query,
    })


@admin_required
@require_POST
def toggle_user_status(request, user_id):
    with transaction.atomic():
        user = get_object_or_404(
            User.objects.select_for_update(),
            pk=user_id,
            is_staff=False,
            is_superuser=False
        )

        user.is_active = not user.is_active
        user.save(update_fields=['is_active'])

        if user.is_active:
            action = 'REACTIVATE'
            description = f'Activated user {user.username}'
        else:
            action = 'ARCHIVE'
            description = f'Deactivated user {user.username}'

        record_audit(request, action, user, description)

    messages.success(request, description)
    return redirect('manage_users')


@admin_required
def user_reservation_history(request, user_id):
    user = get_object_or_404(
        User,
        pk=user_id,
        is_staff=False,
        is_superuser=False
    )

    reservations = user.reservation_set.select_related(
        'facility'
    ).order_by('-created_at')

    return render(request, 'management/user_reservation_history.html', {
        'selected_user': user,
        'reservations': reservations,
    })


@admin_required
def manage_facilities(request):
    search_query = request.GET.get('search', '').strip()

    facilities = Facility.objects.select_related(
        'category'
    ).order_by('name')

    if search_query:
        facilities = facilities.filter(
            Q(name__icontains=search_query) |
            Q(code__icontains=search_query) |
            Q(location__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )

    return render(request, 'management/manage_facilities.html', {
        'facilities': facilities,
        'search_query': search_query,
    })


@admin_required
def add_facility(request):
    if request.method == 'POST':
        form = FacilityForm(request.POST)

        if form.is_valid():
            with transaction.atomic():
                facility = form.save()
                record_audit(
                    request,
                    'CREATE',
                    facility,
                    f'Created facility {facility.name} ({facility.code})'
                )

            messages.success(request, 'Facility added successfully.')
            return redirect('manage_facilities')
    else:
        form = FacilityForm()

    return render(request, 'management/facility_form.html', {
        'form': form,
    })


@admin_required
def edit_facility(request, facility_id):
    facility = get_object_or_404(Facility, pk=facility_id)

    if request.method == 'POST':
        form = FacilityForm(request.POST, instance=facility)

        if form.is_valid():
            with transaction.atomic():
                facility = form.save()
                record_audit(
                    request,
                    'UPDATE',
                    facility,
                    f'Updated facility {facility.name} ({facility.code})'
                )

            messages.success(request, 'Facility updated successfully.')
            return redirect('manage_facilities')
    else:
        form = FacilityForm(instance=facility)

    return render(request, 'management/facility_form.html', {
        'form': form,
        'facility': facility,
        'is_edit': True,
    })


@admin_required
@require_POST
def toggle_facility_status(request, facility_id):
    with transaction.atomic():
        facility = get_object_or_404(
            Facility.objects.select_for_update(),
            pk=facility_id
        )

        if facility.is_active:
            has_upcoming_reservations = Reservation.objects.filter(
                facility=facility,
                status__in=['approved', 'checked_in'],
                end_time__gt=timezone.now()
            ).exists()

            if has_upcoming_reservations:
                messages.error(
                    request,
                    'Cannot archive this facility because it has ongoing '
                    'or upcoming approved reservations.'
                )
                return redirect('manage_facilities')

            facility.is_active = False
            action = 'ARCHIVE'
            description = f'Archived facility {facility.name}'
        else:
            if not facility.category.is_active:
                messages.error(
                    request,
                    'Reactivate the facility category first.'
                )
                return redirect('manage_facilities')

            facility.is_active = True
            action = 'REACTIVATE'
            description = f'Reactivated facility {facility.name}'

        facility.save(update_fields=['is_active'])
        record_audit(request, action, facility, description)

    messages.success(request, description)
    return redirect('manage_facilities')


@admin_required
def manage_categories(request):
    search_query = request.GET.get('search', '').strip()

    categories = FacilityCategory.objects.annotate(
        facility_count=Count('facilities')
    ).order_by('name')

    if search_query:
        categories = categories.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    return render(request, 'management/manage_categories.html', {
        'categories': categories,
        'search_query': search_query,
    })


@admin_required
def add_category(request):
    if request.method == 'POST':
        form = FacilityCategoryForm(request.POST)

        if form.is_valid():
            with transaction.atomic():
                category = form.save()
                record_audit(
                    request,
                    'CREATE',
                    category,
                    f'Created category {category.name}'
                )

            messages.success(request, 'Facility category added successfully.')
            return redirect('manage_categories')
    else:
        form = FacilityCategoryForm()

    return render(request, 'management/category_form.html', {
        'form': form,
    })


@admin_required
def edit_category(request, category_id):
    category = get_object_or_404(FacilityCategory, pk=category_id)

    if request.method == 'POST':
        form = FacilityCategoryForm(request.POST, instance=category)

        if form.is_valid():
            with transaction.atomic():
                category = form.save()
                record_audit(
                    request,
                    'UPDATE',
                    category,
                    f'Updated category {category.name}'
                )

            messages.success(request, 'Facility category updated successfully.')
            return redirect('manage_categories')
    else:
        form = FacilityCategoryForm(instance=category)

    return render(request, 'management/category_form.html', {
        'form': form,
        'category': category,
        'is_edit': True,
    })


@admin_required
@require_POST
def toggle_category_status(request, category_id):
    with transaction.atomic():
        category = get_object_or_404(
            FacilityCategory.objects.select_for_update(),
            pk=category_id
        )

        if category.is_active:
            has_active_facilities = Facility.objects.filter(
                category=category,
                is_active=True
            ).exists()

            if has_active_facilities:
                messages.error(
                    request,
                    'Cannot archive this category because '
                    'it still contains active facilities.'
                )
                return redirect('manage_categories')

            category.is_active = False
            action = 'ARCHIVE'
            description = f'Archived category {category.name}'
        else:
            category.is_active = True
            action = 'REACTIVATE'
            description = f'Reactivated category {category.name}'

        category.save(update_fields=['is_active'])
        record_audit(request, action, category, description)

    messages.success(request, description)
    return redirect('manage_categories')


@admin_required
def manage_amenities(request):
    search_query = request.GET.get('search', '').strip()

    amenities = Amenity.objects.all().order_by('name')

    if search_query:
        amenities = amenities.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    return render(request, 'management/manage_amenities.html', {
        'amenities': amenities,
        'search_query': search_query,
    })


@admin_required
def add_amenity(request):
    if request.method == 'POST':
        form = AmenityForm(request.POST)

        if form.is_valid():
            with transaction.atomic():
                amenity = form.save()
                record_audit(
                    request,
                    'CREATE',
                    amenity,
                    f'Created amenity {amenity.name}'
                )

            messages.success(request, 'Amenity added successfully.')
            return redirect('manage_amenities')
    else:
        form = AmenityForm()

    return render(request, 'management/amenity_form.html', {
        'form': form,
    })


@admin_required
def edit_amenity(request, amenity_id):
    amenity = get_object_or_404(Amenity, pk=amenity_id)

    if request.method == 'POST':
        form = AmenityForm(request.POST, instance=amenity)

        if form.is_valid():
            with transaction.atomic():
                amenity = form.save()
                record_audit(
                    request,
                    'UPDATE',
                    amenity,
                    f'Updated amenity {amenity.name}'
                )

            messages.success(request, 'Amenity updated successfully.')
            return redirect('manage_amenities')
    else:
        form = AmenityForm(instance=amenity)

    return render(request, 'management/amenity_form.html', {
        'form': form,
        'amenity': amenity,
        'is_edit': True,
    })


@admin_required
@require_POST
def toggle_amenity_status(request, amenity_id):
    with transaction.atomic():
        amenity = get_object_or_404(
            Amenity.objects.select_for_update(),
            pk=amenity_id
        )

        if amenity.is_active:
            amenity.is_active = False
            action = 'ARCHIVE'
            description = f'Archived amenity {amenity.name}'
        else:
            amenity.is_active = True
            action = 'REACTIVATE'
            description = f'Reactivated amenity {amenity.name}'

        amenity.save(update_fields=['is_active'])
        record_audit(request, action, amenity, description)

    messages.success(request, description)
    return redirect('manage_amenities')

@admin_required
def manage_reservations(request):

    # Get filter values from the URL
    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip()
    facility_filter = request.GET.get('facility', '').strip()
    date_filter = request.GET.get('date', '').strip()

    date_error = ''

    # Retrieve reservation records
    reservations = Reservation.objects.select_related(
        'user',
        'facility'
    ).order_by('-created_at')

    # Search reservations by username, facility,
    # event title, or event purpose
    if search_query:

        reservations = reservations.filter(
            Q(user__username__icontains=search_query)
            | Q(facility__name__icontains=search_query)
            | Q(event_title__icontains=search_query)
            | Q(purpose__icontains=search_query)
        )

    # Filter by reservation status
    valid_statuses = dict(Reservation.STATUS_CHOICES)

    if status_filter:

        if status_filter in valid_statuses:
            reservations = reservations.filter(
                status=status_filter
            )
        else:
            reservations = reservations.none()

    # Filter by selected facility
    if facility_filter:

        if (
            facility_filter.isascii()
            and facility_filter.isdigit()
            and len(facility_filter) <= 12
        ):
            reservations = reservations.filter(
                facility_id=int(facility_filter)
            )

        else:
            reservations = reservations.none()

    # Filter by reservation start date
    if date_filter:

        try:
            selected_date = date.fromisoformat(
                date_filter
            )

            reservations = reservations.filter(
                start_time__date=selected_date
            )

        except (ValueError, TypeError):

            reservations = reservations.none()

            date_error = (
                'Please enter a valid reservation date.'
            )

    # Paginate results (10 reservations per page)
    paginator = Paginator(reservations, 10)

    page_obj = paginator.get_page(
        request.GET.get('page')
    )

    # Retrieve all facilities for dropdown
    facilities = Facility.objects.order_by('name')

    return render(
        request,
        'management/manage_reservations.html',
        {
            'page_obj': page_obj,

            'search_query': search_query,
            'status_filter': status_filter,
            'facility_filter': facility_filter,
            'date_filter': date_filter,

            'date_error': date_error,

            'status_choices': Reservation.STATUS_CHOICES,
            'facilities': facilities,
        }
    )

@admin_required
@require_POST
def update_reservation_status(request, reservation_id):

    action = request.POST.get('action', '')
    reason = request.POST.get('reason', '')

    try:

        reservation = update_reservation(
            request,
            reservation_id,
            action,
            reason
        )

        messages.success(
            request,
            f'Reservation #{reservation.pk} '
            f'has been updated to {reservation.get_status_display()}.'
        )

    except ValidationError as error:

        messages.error(
            request,
            '; '.join(error.messages)
        )

    except Reservation.DoesNotExist:

        raise Http404('Reservation not found.')

    except DatabaseError:

        messages.error(
            request,
            'The reservation could not be updated due to '
            'a database conflict. Please try again.'
        )

    return redirect('manage_reservations')


@admin_required
def view_audit_logs(request):
    search_query = request.GET.get('search', '').strip()
    action_filter = request.GET.get('action', '').strip()

    logs = AuditLog.objects.select_related(
        'admin_user'
    ).order_by('-timestamp')

    if search_query:
        logs = logs.filter(
            Q(admin_user__username__icontains=search_query) |
            Q(model_name__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    valid_actions = dict(AuditLog.ACTION_CHOICES)

    if action_filter in valid_actions:
        logs = logs.filter(action=action_filter)

    paginator = Paginator(logs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'management/audit_logs.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'action_filter': action_filter,
        'action_choices': AuditLog.ACTION_CHOICES,
    })

@admin_required
def reservation_history(request, reservation_id):

    reservation = get_object_or_404(
        Reservation.objects.select_related(
            'user',
            'facility',
            'decision_by'
        ),
        pk=reservation_id
    )

    changes = ReservationChange.objects.filter(
        reservation=reservation
    ).select_related(
        'changed_by'
    ).order_by('-changed_at')

    return render(
        request,
        'management/reservation_history.html',
        {
            'reservation': reservation,
            'changes': changes,
        }
    )

@admin_required
def reservation_calendar(request):

    selected_view = request.GET.get('view', 'week')

    if selected_view not in ['day', 'week']:
        selected_view = 'week'

    selected_date_string = request.GET.get('date', '')

    try:
        selected_date = date.fromisoformat(
            selected_date_string
        )
    except ValueError:
        selected_date = timezone.localdate()

    if selected_view == 'week':

        start_date = selected_date - timedelta(
            days=selected_date.weekday()
        )

        end_date = start_date + timedelta(days=6)

        previous_date = start_date - timedelta(days=7)
        next_date = start_date + timedelta(days=7)

    else:

        start_date = selected_date
        end_date = selected_date

        previous_date = selected_date - timedelta(days=1)
        next_date = selected_date + timedelta(days=1)

    current_timezone = timezone.get_current_timezone()

    start_datetime = timezone.make_aware(
        datetime.combine(
            start_date,
            time.min
        ),
        current_timezone
    )

    end_datetime = timezone.make_aware(
        datetime.combine(
            end_date + timedelta(days=1),
            time.min
        ),
        current_timezone
    )

    reservations = (
        Reservation.objects
        .filter(
            status__in=[
                'approved',
                'checked_in',
                'completed',
                'no_show'
            ],
            start_time__gte=start_datetime,
            start_time__lt=end_datetime
        )
        .select_related(
            'facility',
            'user'
        )
        .order_by(
            'start_time'
        )
    )

    calendar_days = []

    number_of_days = (
        end_date - start_date
    ).days + 1

    for day_number in range(number_of_days):

        current_date = start_date + timedelta(
            days=day_number
        )

        day_reservations = [
            reservation
            for reservation in reservations
            if timezone.localtime(
                reservation.start_time
            ).date() == current_date
        ]

        calendar_days.append({
            'date': current_date,
            'reservations': day_reservations
        })

    return render(
        request,
        'management/reservation_calendar.html',
        {
            'calendar_days': calendar_days,
            'selected_date': selected_date,
            'selected_view': selected_view,
            'start_date': start_date,
            'end_date': end_date,
            'previous_date': previous_date,
            'next_date': next_date
        }
    )

@admin_required
def reschedule_reservation_view(
    request,
    reservation_id
):

    reservation = get_object_or_404(
        Reservation.objects.select_related(
            'facility',
            'user'
        ),
        pk=reservation_id
    )

    if request.method == 'POST':

        new_start = request.POST.get(
            'start_time',
            ''
        )

        new_end = request.POST.get(
            'end_time',
            ''
        )

        reason = request.POST.get(
            'reason',
            ''
        )

        try:

            updated_reservation = reschedule_reservation(
                request,
                reservation_id,
                new_start,
                new_end,
                reason
            )

            messages.success(
                request,
                f'Reservation #{updated_reservation.pk} '
                f'has been successfully rescheduled.'
            )

            return redirect(
                'reservation_history',
                reservation_id=reservation_id
            )

        except ValidationError as error:

            messages.error(
                request,
                '; '.join(error.messages)
            )

        except DatabaseError:

            messages.error(
                request,
                'The reservation could not be rescheduled '
                'because of a database conflict. '
                'Please try again.'
            )

    start_value = timezone.localtime(
        reservation.start_time
    ).strftime('%Y-%m-%dT%H:%M')

    end_value = timezone.localtime(
        reservation.end_time
    ).strftime('%Y-%m-%dT%H:%M')

    return render(
        request,
        'management/reschedule_reservation.html',
        {
            'reservation': reservation,
            'start_value': start_value,
            'end_value': end_value
        }
    )

@admin_required
def event_monitoring(request):

    selected_date_string = request.GET.get('date', '')

    try:
        selected_date = date.fromisoformat(selected_date_string)
    except ValueError:
        selected_date = timezone.localdate()

    current_timezone = timezone.get_current_timezone()

    start_datetime = timezone.make_aware(
        datetime.combine(selected_date, time.min),
        current_timezone
    )

    end_datetime = timezone.make_aware(
        datetime.combine(
            selected_date + timedelta(days=1),
            time.min
        ),
        current_timezone
    )

    reservations = Reservation.objects.filter(
        status__in=[
            'approved',
            'checked_in',
            'completed',
            'no_show'
        ],
        start_time__gte=start_datetime,
        start_time__lt=end_datetime
    ).select_related(
        'user',
        'facility'
    ).order_by('start_time')

    return render(
        request,
        'management/event_monitoring.html',
        {
            'reservations': reservations,
            'selected_date': selected_date
        }
    )

@admin_required
def event_detail(request, reservation_id):

    reservation = get_object_or_404(
        Reservation.objects.select_related(
            'user',
            'facility'
        ),
        pk=reservation_id
    )

    event_record = EventRecord.objects.filter(
        reservation=reservation
    ).first()

    incidents = EventIncident.objects.filter(
        event_record=event_record
    ).select_related('reported_by') if event_record else []

    return render(
        request,
        'management/event_detail.html',
        {
            'reservation': reservation,
            'event_record': event_record,
            'incidents': incidents
        }
    )

@admin_required
@require_POST
def report_event_incident(request, reservation_id):

    reservation = get_object_or_404(
        Reservation,
        pk=reservation_id
    )

    description = request.POST.get(
        'description',
        ''
    ).strip()

    if not description:
        messages.error(
            request,
            'Please enter an incident description.'
        )

        return redirect(
            'event_detail',
            reservation_id=reservation_id
        )

    if reservation.status not in [
        'checked_in',
        'completed',
        'no_show'
    ]:
        messages.error(
            request,
            'Incidents can only be recorded for '
            'checked-in, completed, or no-show events.'
        )

        return redirect(
            'event_detail',
            reservation_id=reservation_id
        )

    try:
        with transaction.atomic():

            event_record = EventRecord.objects.get(
                reservation=reservation
            )

            incident = EventIncident.objects.create(
                event_record=event_record,
                description=description,
                reported_by=request.user
            )

            record_audit(
                request,
                'CREATE',
                incident,
                (
                    f'Incident recorded for reservation '
                    f'#{reservation.pk}. '
                    f'Description: {description}'
                )
            )

    except EventRecord.DoesNotExist:

        messages.error(
            request,
            'This event does not have an event record yet.'
        )

        return redirect(
            'event_detail',
            reservation_id=reservation_id
        )

    messages.success(
        request,
        'Incident report saved successfully.'
    )

    return redirect(
        'event_detail',
        reservation_id=reservation_id
    )

@admin_required
def printable_event_slip(request, reservation_id):

    reservation = get_object_or_404(
        Reservation.objects.select_related(
            'user',
            'facility',
            'decision_by'
        ),
        pk=reservation_id
    )

    if reservation.status not in [
        'approved',
        'checked_in',
        'completed',
        'no_show'
    ]:
        messages.error(
            request,
            'Only approved or recorded events have printable slips.'
        )

        return redirect('event_monitoring')

    event_record = EventRecord.objects.filter(
        reservation=reservation
    ).select_related(
        'checked_in_by',
        'completed_by',
        'no_show_marked_by'
    ).first()

    return render(
        request,
        'management/event_slip.html',
        {
            'reservation': reservation,
            'event_record': event_record
        }
    )


@admin_required
def manage_closures(request):
    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', 'active')

    closures = FacilityClosure.objects.select_related(
        'facility',
        'created_by'
    )

    if search_query:
        closures = closures.filter(
            Q(facility__name__icontains=search_query)
            | Q(facility__code__icontains=search_query)
            | Q(reason__icontains=search_query)
        )

    if status_filter == 'active':
        closures = closures.filter(is_active=True)
    elif status_filter == 'archived':
        closures = closures.filter(is_active=False)

    page_obj = Paginator(
        closures.order_by('-start_time'), 10
    ).get_page(request.GET.get('page'))

    return render(request, 'management/manage_closures.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
    })


def _closure_preview_context(form, exclude_closure_id=None):
    """
    Inspect submitted closure dates without saving anything.

    This performs field-level validation separately because
    the FacilityClosure model rejects conflicting bookings
    during normal form validation.
    """

    context = {
        'preview_requested': True,
        'preview_ready': False,
        'preview_reservations': [],
        'preview_closures': [],
        'preview_has_conflicts': False,
    }

    try:
        facility = form.fields['facility'].clean(
            form.data.get('facility')
        )

        start_time = form.fields['start_time'].clean(
            form.data.get('start_time')
        )

        end_time = form.fields['end_time'].clean(
            form.data.get('end_time')
        )

    except ValidationError:
        return context

    if (
        facility is None
        or start_time is None
        or end_time is None
        or end_time <= start_time
    ):
        return context

    reservations = list(
        Reservation.objects.filter(
            facility=facility,
            status__in=['approved', 'checked_in'],
            start_time__lt=end_time,
            end_time__gt=start_time
        )
        .select_related('user', 'facility')
        .order_by('start_time')
    )

    existing_closures = list(
        FacilityClosure.objects.filter(
            facility=facility,
            is_active=True,
            start_time__lt=end_time,
            end_time__gt=start_time
        )
        .exclude(pk=exclude_closure_id)
        .order_by('start_time')
    )

    context.update({
        'preview_ready': True,
        'preview_reservations': reservations,
        'preview_closures': existing_closures,
        'preview_has_conflicts': bool(
            reservations or existing_closures
        ),
    })

    return context

@admin_required
def add_closure(request):

    preview_context = {}

    if request.method == 'POST':

        form = FacilityClosureForm(request.POST)

        if request.POST.get('action') == 'preview':

            preview_context = _closure_preview_context(form)

            form.is_valid()

            return render(
                request,
                'management/closure_form.html',
                {
                    'form': form,
                    'page_title': 'Add Facility Closure',
                    **preview_context,
                }
            )

        if form.is_valid():

            try:
                with transaction.atomic():

                    closure = form.save(commit=False)

                    closure.created_by = request.user

                    Facility.objects.filter(
                        pk=closure.facility_id
                    ).update(
                        is_active=F('is_active')
                    )

                    closure.full_clean()
                    closure.save()

                    record_audit(
                        request,
                        'CREATE',
                        closure,
                        (
                            f'Created closure #{closure.pk} '
                            f'for {closure.facility.name}. '
                            f'From {closure.start_time} '
                            f'to {closure.end_time}. '
                            f'Reason: {closure.reason}'
                        )
                    )

                messages.success(
                    request,
                    'Facility closure created successfully.'
                )

                return redirect('manage_closures')

            except ValidationError as error:
                form.add_error(None, error)

            except DatabaseError:
                messages.error(
                    request,
                    'The closure could not be saved due to '
                    'a database conflict. Please try again.'
                )

    else:
        form = FacilityClosureForm()

    return render(
        request,
        'management/closure_form.html',
        {
            'form': form,
            'page_title': 'Add Facility Closure',
            **preview_context,
        }
    )


@admin_required
def edit_closure(request, closure_id):

    closure = get_object_or_404(
        FacilityClosure,
        pk=closure_id
    )

    if not closure.is_active:
        messages.error(
            request,
            'Archived closures cannot be edited.'
        )
        return redirect('manage_closures')

    preview_context = {}

    if request.method == 'POST':

        old_facility_id = closure.facility_id

        form = FacilityClosureForm(
            request.POST,
            instance=closure
        )

        if request.POST.get('action') == 'preview':

            preview_context = _closure_preview_context(
                form,
                exclude_closure_id=closure.pk
            )

            form.is_valid()

            return render(
                request,
                'management/closure_form.html',
                {
                    'form': form,
                    'page_title': 'Edit Facility Closure',
                    **preview_context,
                }
            )

        if form.is_valid():

            try:
                with transaction.atomic():

                    updated_closure = form.save(
                        commit=False
                    )

                    Facility.objects.filter(
                        pk__in=[
                            old_facility_id,
                            updated_closure.facility_id
                        ]
                    ).order_by('pk').update(
                        is_active=F('is_active')
                    )

                    current_closure = (
                        FacilityClosure.objects
                        .select_for_update()
                        .get(pk=closure_id)
                    )

                    if not current_closure.is_active:
                        raise ValidationError(
                            'Archived closures cannot be edited.'
                        )

                    updated_closure.created_by = (
                        current_closure.created_by
                    )

                    updated_closure.full_clean()
                    updated_closure.save()

                    record_audit(
                        request,
                        'UPDATE',
                        updated_closure,
                        (
                            f'Updated closure '
                            f'#{updated_closure.pk}. '
                            f'Facility: '
                            f'{updated_closure.facility.name}. '
                            f'From {updated_closure.start_time} '
                            f'to {updated_closure.end_time}. '
                            f'Reason: {updated_closure.reason}'
                        )
                    )

                messages.success(
                    request,
                    'Facility closure updated successfully.'
                )

                return redirect('manage_closures')

            except ValidationError as error:
                form.add_error(None, error)

            except DatabaseError:
                messages.error(
                    request,
                    'The closure could not be updated '
                    'due to a database conflict. '
                    'Please try again.'
                )

    else:
        form = FacilityClosureForm(
            instance=closure
        )

    return render(
        request,
        'management/closure_form.html',
        {
            'form': form,
            'page_title': 'Edit Facility Closure',
            **preview_context,
        }
    )


@admin_required
@require_POST
def archive_closure(request, closure_id):
    reference = get_object_or_404(FacilityClosure, pk=closure_id)

    try:
        with transaction.atomic():
            Facility.objects.filter(
                pk=reference.facility_id
            ).update(is_active=F('is_active'))

            closure = get_object_or_404(
                FacilityClosure.objects.select_for_update(),
                pk=closure_id
            )

            if not closure.is_active:
                messages.error(request, 'This closure is already archived.')
                return redirect('manage_closures')

            closure.is_active = False
            closure.save(update_fields=['is_active'])

            record_audit(
                request,
                'ARCHIVE',
                closure,
                f'Archived closure #{closure.pk} for {closure.facility.name}.'
            )

        messages.success(request, 'Facility closure archived successfully.')
    except DatabaseError:
        messages.error(
            request,
            'The closure could not be archived due to a database conflict. Please try again.'
        )

    return redirect('manage_closures')


def _shift_month(value, offset):
    month_index = value.year * 12 + value.month - 1 + offset
    year, month_zero = divmod(month_index, 12)
    return date(year, month_zero + 1, 1)


def _add_chart_widths(rows):
    highest = max((row['count'] for row in rows), default=0)
    for row in rows:
        row['width'] = round(row['count'] * 100 / highest) if highest else 0


def _get_report_filters(request):
    today = timezone.localdate()
    first_day = today.replace(day=1)
    last_day = today.replace(day=calendar.monthrange(today.year, today.month)[1])
    start_value = request.GET.get('start_date', first_day.isoformat()).strip()
    end_value = request.GET.get('end_date', last_day.isoformat()).strip()
    status = request.GET.get('status', '').strip()
    facility_value = request.GET.get('facility', '').strip()
    error = ''

    try:
        start_date = date.fromisoformat(start_value)
        end_date = date.fromisoformat(end_value)
        if start_date > end_date:
            error = 'Start date must be on or before end date.'
    except ValueError:
        start_date = first_day
        end_date = last_day
        error = 'Enter valid start and end dates.'

    valid_statuses = dict(Reservation.STATUS_CHOICES)
    if status and status not in valid_statuses:
        error = 'Invalid reservation status.'
    if facility_value and (not facility_value.isdecimal() or not Facility.objects.filter(pk=facility_value).exists()):
        error = 'Invalid facility selection.'

    queryset = Reservation.objects.select_related('user', 'facility').order_by('-start_time', '-pk')
    if error:
        queryset = queryset.none()
    else:
        queryset = queryset.filter(start_time__date__range=(start_date, end_date))
        if status:
            queryset = queryset.filter(status=status)
        if facility_value:
            queryset = queryset.filter(facility_id=int(facility_value))

    return {
        'queryset': queryset,
        'start_date': start_date,
        'end_date': end_date,
        'status_filter': status,
        'facility_filter': facility_value,
        'error': error,
    }


def _facility_utilization_rows(filters):

    if filters['error']:
        return []

    booked_statuses = (
        'approved',
        'checked_in',
        'completed',
        'no_show'
    )

    duration_expression = ExpressionWrapper(
        F('end_time') - F('start_time'),
        output_field=DurationField()
    )

    aggregates = (
        filters['queryset']
        .order_by()
        .values('facility_id')
        .annotate(
            booked_duration=Sum(
                duration_expression,
                filter=Q(status__in=booked_statuses)
            ),

            completed_events=Count(
                'id',
                filter=Q(status='completed')
            )
        )
    )

    by_facility = {
        row['facility_id']: row
        for row in aggregates
    }

    facilities = Facility.objects.order_by(
        'name',
        'pk'
    )

    if filters['facility_filter']:
        facilities = facilities.filter(
            pk=int(filters['facility_filter'])
        )

    utilization_rows = []

    for facility in facilities:

        summary = by_facility.get(
            facility.pk,
            {}
        )

        booked_duration = (
            summary.get('booked_duration')
            or timedelta()
        )

        booked_hours = round(
            booked_duration.total_seconds() / 3600,
            2
        )

        utilization_rows.append({
            'facility_code': facility.code or 'No code',
            'facility_name': facility.name,
            'booked_hours': booked_hours,
            'completed_events': summary.get(
                'completed_events',
                0
            )
        })

    return utilization_rows


@admin_required
def reservation_reports(request):

    filters = _get_report_filters(request)

    queryset = filters['queryset']

    booked_statuses = [
        'approved',
        'checked_in',
        'completed',
        'no_show'
    ]

    duration = queryset.filter(
        status__in=booked_statuses
    ).aggregate(
        total=Sum(
            ExpressionWrapper(
                F('end_time') - F('start_time'),
                output_field=DurationField()
            )
        )
    )['total'] or timedelta()

    page_obj = Paginator(
        queryset,
        20
    ).get_page(
        request.GET.get('page')
    )

    utilization_rows = _facility_utilization_rows(
        filters
    )

    return render(
        request,
        'management/reports.html',
        {
            **filters,

            'page_obj': page_obj,

            'facilities': Facility.objects.order_by(
                'name'
            ),

            'status_choices': Reservation.STATUS_CHOICES,

            'total_reservations': queryset.count(),

            'approved_count': queryset.filter(
                status='approved'
            ).count(),

            'completed_count': queryset.filter(
                status='completed'
            ).count(),

            'booked_hours': round(
                duration.total_seconds() / 3600,
                2
            ),

            'utilization_rows': utilization_rows,
        }
    )

def _csv_safe(value):
    text = '' if value is None else str(value)
    if text.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')):
        return "'" + text
    return text


@admin_required
def export_reservation_report(request):
    filters = _get_report_filters(request)
    if filters['error']:
        messages.error(request, filters['error'])
        return redirect('reservation_reports')

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = (
        f'attachment; filename="reservation_report_{filters["start_date"]}_{filters["end_date"]}.csv"'
    )
    response.write('\ufeff')
    writer = csv.writer(response)
    writer.writerow([
        'Reservation ID', 'Username', 'Facility Code', 'Facility Name',
        'Event Title', 'Purpose', 'Participants', 'Start (Asia/Manila)',
        'End (Asia/Manila)', 'Booked Hours', 'Status', 'Decision Reason',
    ])

    for reservation in filters['queryset'].iterator():
        hours = (reservation.end_time - reservation.start_time).total_seconds() / 3600
        writer.writerow([
            reservation.pk,
            _csv_safe(reservation.user.username),
            _csv_safe(reservation.facility.code),
            _csv_safe(reservation.facility.name),
            _csv_safe(reservation.event_title),
            _csv_safe(reservation.purpose),
            reservation.participant_count,
            timezone.localtime(reservation.start_time).strftime('%Y-%m-%d %H:%M'),
            timezone.localtime(reservation.end_time).strftime('%Y-%m-%d %H:%M'),
            round(hours, 2),
            reservation.get_status_display(),
            _csv_safe(reservation.decision_reason),
        ])

    return response


@admin_required
def export_utilization_report(request):

    filters = _get_report_filters(request)

    if filters['error']:

        messages.error(
            request,
            filters['error']
        )

        return redirect('reservation_reports')

    utilization_rows = _facility_utilization_rows(
        filters
    )

    response = HttpResponse(
        content_type='text/csv; charset=utf-8'
    )

    response['Content-Disposition'] = (
        f'attachment; filename="facility_utilization_'
        f'{filters["start_date"]}_{filters["end_date"]}.csv"'
    )

    response.write('\ufeff')

    writer = csv.writer(response)

    writer.writerow([
        'Facility Code',
        'Facility Name',
        'Booked Hours',
        'Completed Events'
    ])

    for row in utilization_rows:

        writer.writerow([
            _csv_safe(row['facility_code']),
            _csv_safe(row['facility_name']),
            row['booked_hours'],
            row['completed_events']
        ])

    return response
