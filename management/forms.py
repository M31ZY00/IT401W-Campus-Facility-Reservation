from django import forms
from facilities.models import Facility, FacilityCategory, Amenity
from django.db.models import Q
from .models import SystemSetting

class FacilityForm(forms.ModelForm):
    class Meta:
        model = Facility

        fields = [
            'code',
            'name',
            'category',
            'location',
            'capacity',
            'description',
            'opening_time',
            'closing_time',
            'amenities',
            'is_active',
        ]

        widgets = {
            'opening_time': forms.TimeInput(
                attrs={'type': 'time'},
                format='%H:%M'
            ),
            'closing_time': forms.TimeInput(
                attrs={'type': 'time'},
                format='%H:%M'
            ),
            'amenities': forms.CheckboxSelectMultiple(),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['code'].required = True
        self.fields['category'].required = True

        categories = FacilityCategory.objects.filter(
            is_active=True
        )

        if self.instance.pk and self.instance.category_id:
            categories = FacilityCategory.objects.filter(
                Q(is_active=True) |
                Q(pk=self.instance.category_id)
            )

        self.fields['category'].queryset = categories

        amenities = Amenity.objects.filter(
            is_active=True
        )

        if self.instance.pk:
            existing_amenities = self.instance.amenities.values_list(
                'pk',
                flat=True
            )

            amenities = Amenity.objects.filter(
                Q(is_active=True) |
                Q(pk__in=existing_amenities)
            )

        self.fields['amenities'].queryset = amenities

    def clean_code(self):
        code = (self.cleaned_data.get('code') or '').strip().upper()

        if not code:
            raise forms.ValidationError(
                'Facility code is required.'
            )

        return code

    def clean_capacity(self):
        capacity = self.cleaned_data.get('capacity')

        if capacity is not None and capacity < 1:
            raise forms.ValidationError(
                'Capacity must be at least 1.'
            )

        return capacity

    def clean(self):
        cleaned_data = super().clean()

        opening_time = cleaned_data.get('opening_time')
        closing_time = cleaned_data.get('closing_time')

        if opening_time and closing_time:
            if closing_time <= opening_time:
                self.add_error(
                    'closing_time',
                    'Closing time must be later than opening time.'
                )

        return cleaned_data

class FacilityCategoryForm(forms.ModelForm):
    class Meta:
        model = FacilityCategory

        fields = [
            'name',
            'description',
        ]

        widgets = {
            'name': forms.TextInput(
                attrs={'placeholder': 'Enter category name'}
            ),
            'description': forms.Textarea(
                attrs={
                    'rows': 4,
                    'placeholder': 'Enter category description'
                }
            ),
        }

    def clean_name(self):
        name = self.cleaned_data['name'].strip()

        if not name:
            raise forms.ValidationError(
                'Category name is required.'
            )

        if FacilityCategory.objects.filter(
            name__iexact=name
        ).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError(
                'A category with this name already exists.'
            )

        return name


class AmenityForm(forms.ModelForm):
    class Meta:
        model = Amenity

        fields = [
            'name',
            'description',
        ]

        widgets = {
            'name': forms.TextInput(
                attrs={
                    'placeholder': 'Enter amenity name'
                }
            ),
            'description': forms.Textarea(
                attrs={
                    'rows': 4,
                    'placeholder': 'Enter amenity description'
                }
            ),
        }

    def clean_name(self):
        name = self.cleaned_data['name'].strip()

        if not name:
            raise forms.ValidationError(
                'Amenity name is required.'
            )

        if Amenity.objects.filter(
            name__iexact=name
        ).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError(
                'An amenity with this name already exists.'
            )

        return name

class SystemSettingForm(forms.ModelForm):
    class Meta:
        model = SystemSetting

        fields = [
            'max_booking_hours',
            'advance_booking_days'
        ]

        labels = {
            'max_booking_hours': 'Maximum Booking Duration (Hours)',
            'advance_booking_days': 'Advance Booking Window (Days)'
        }

        widgets = {
            'max_booking_hours': forms.NumberInput(
                attrs={
                    'min': 1,
                    'max': 24
                }
            ),
            'advance_booking_days': forms.NumberInput(
                attrs={
                    'min': 1,
                    'max': 365
                }
            )
        }