from django import forms
from django.db.models import Q

from .models import Facility, FacilityClosure


class FacilityClosureForm(forms.ModelForm):

    class Meta:
        model = FacilityClosure

        fields = [
            'facility',
            'start_time',
            'end_time',
            'reason'
        ]

        widgets = {
            'start_time': forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M'
            ),
            'end_time': forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M'
            ),
            'reason': forms.Textarea(
                attrs={'rows': 4}
            )
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['start_time'].input_formats = [
            '%Y-%m-%dT%H:%M',
            '%Y-%m-%d %H:%M:%S'
        ]

        self.fields['end_time'].input_formats = [
            '%Y-%m-%dT%H:%M',
            '%Y-%m-%d %H:%M:%S'
        ]

        facility_filter = Q(is_active=True)

        if self.instance.pk:
            facility_filter |= Q(pk=self.instance.facility_id)

        self.fields['facility'].queryset = (
            Facility.objects
            .filter(facility_filter)
            .distinct()
            .order_by('name')
        )