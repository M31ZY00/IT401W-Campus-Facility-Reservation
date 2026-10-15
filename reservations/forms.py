from django import forms
from django.utils import timezone
from .models import Reservation


class ReservationForm(forms.ModelForm):

    class Meta:
        model = Reservation
        fields = [
            'event_title',
            'purpose',
            'participant_count',
            'start_time',
            'end_time'
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
            'purpose': forms.Textarea(
                attrs={'rows': 4}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['start_time'].input_formats = ['%Y-%m-%dT%H:%M']
        self.fields['end_time'].input_formats = ['%Y-%m-%dT%H:%M']

    def clean(self):
        cleaned_data = super().clean()

        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')

        if start_time and start_time < timezone.now():
            self.add_error(
                'start_time',
                'You cannot reserve a facility in the past.'
            )

        if start_time and end_time and end_time <= start_time:
            self.add_error(
                'end_time',
                'End time must be later than start time.'
            )

        return cleaned_data