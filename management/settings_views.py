from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, redirect
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_http_methods

from .audit import record_audit
from .forms import SystemSettingForm
from .models import AuditLog, SystemSetting


def administrator_required(view_func):
    @login_required(login_url='admin_login')
    def wrapper(request, *args, **kwargs):
        if not request.user.is_active or not request.user.is_staff:
            raise PermissionDenied

        return view_func(request, *args, **kwargs)

    return wrapper


@administrator_required
def audit_log_list(request):
    logs = AuditLog.objects.select_related(
        'admin_user'
    ).all()

    search = request.GET.get('search', '').strip()
    action = request.GET.get('action', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()

    if search:
        search_filter = (
            Q(admin_user__username__icontains=search)
            | Q(model_name__icontains=search)
            | Q(description__icontains=search)
            | Q(action__icontains=search)
        )

        if search.isdigit():
            search_filter |= Q(object_id=int(search))

        logs = logs.filter(search_filter)

    valid_actions = {
        choice[0]
        for choice in AuditLog.ACTION_CHOICES
    }

    if action in valid_actions:
        logs = logs.filter(action=action)

    parsed_date_from = parse_date(date_from)

    if parsed_date_from:
        logs = logs.filter(
            timestamp__date__gte=parsed_date_from
        )

    parsed_date_to = parse_date(date_to)

    if parsed_date_to:
        logs = logs.filter(
            timestamp__date__lte=parsed_date_to
        )

    paginator = Paginator(logs, 20)

    page_obj = paginator.get_page(
        request.GET.get('page')
    )

    context = {
        'page_obj': page_obj,
        'search': search,
        'selected_action': action,
        'date_from': date_from,
        'date_to': date_to,
        'action_choices': AuditLog.ACTION_CHOICES,
        'total_logs': paginator.count
    }

    return render(
        request,
        'management/audit_logs.html',
        context
    )


@administrator_required
@require_http_methods(['GET', 'POST'])
def system_settings(request):
    setting = SystemSetting.get_current()

    if request.method == 'POST':
        form = SystemSettingForm(
            request.POST,
            instance=setting
        )

        if form.is_valid():
            old_hours = setting.max_booking_hours
            old_days = setting.advance_booking_days

            updated_setting = form.save(
                commit=False
            )

            updated_setting.updated_by = request.user
            updated_setting.save()

            record_audit(
                request,
                'UPDATE',
                updated_setting,
                (
                    f'System settings updated. '
                    f'Maximum booking duration: '
                    f'{old_hours} to '
                    f'{updated_setting.max_booking_hours} hours. '
                    f'Advance booking window: '
                    f'{old_days} to '
                    f'{updated_setting.advance_booking_days} days.'
                )
            )

            messages.success(
                request,
                'System settings updated successfully.'
            )

            return redirect('system_settings')

    else:
        form = SystemSettingForm(
            instance=setting
        )

    return render(
        request,
        'management/system_settings.html',
        {
            'form': form,
            'setting': setting
        }
    )