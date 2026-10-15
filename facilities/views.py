from django.shortcuts import render, get_object_or_404
from .models import Facility


def facility_list(request):
    facilities = Facility.objects.filter(is_active=True)

    return render(request, 'facilities/facility_list.html', {
        'facilities': facilities
    })


def facility_detail(request, facility_id):
    facility = get_object_or_404(
        Facility,
        id=facility_id,
        is_active=True
    )

    return render(request, 'facilities/facility_detail.html', {
        'facility': facility
    })