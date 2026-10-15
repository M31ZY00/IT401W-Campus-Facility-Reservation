from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone

class FacilityCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = 'Facility Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class Amenity(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = 'Amenities'
        ordering = ['name']

    def __str__(self):
        return self.name


class Facility(models.Model):
    category = models.ForeignKey(
        FacilityCategory,
        on_delete=models.PROTECT,
        related_name='facilities',
        null=True,
        blank=True
    )

    amenities = models.ManyToManyField(
        Amenity,
        related_name='facilities',
        blank=True
    )

    name = models.CharField(max_length=100)
    location = models.CharField(max_length=200)
    capacity = models.PositiveIntegerField()
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    code = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True
    )

    opening_time = models.TimeField(
        default="08:00"
    )

    closing_time = models.TimeField(
        default="17:00"
    )

    def __str__(self):
        return self.name


class FacilityClosure(models.Model):

    facility = models.ForeignKey(
        'Facility',
        on_delete=models.PROTECT,
        related_name='closures'
    )

    start_time = models.DateTimeField()

    end_time = models.DateTimeField()

    reason = models.TextField()

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        super().clean()

        errors = {}

        if not self.start_time or not self.end_time:
            return

        if self.end_time <= self.start_time:
            errors['end_time'] = (
                'End time must be later than start time.'
            )

        if self.is_active:

            if self.start_time <= timezone.now() and not self.pk:
                errors['start_time'] = (
                    'Closure start time must be in the future.'
                )

            if self.facility_id:

                overlapping_closures = FacilityClosure.objects.filter(
                    facility_id=self.facility_id,
                    is_active=True,
                    start_time__lt=self.end_time,
                    end_time__gt=self.start_time
                ).exclude(
                    pk=self.pk
                )

                if overlapping_closures.exists():
                    errors['start_time'] = (
                        'This facility already has an active closure '
                        'during the selected schedule.'
                    )

                from reservations.models import Reservation

                conflicting_reservations = Reservation.objects.filter(
                    facility_id=self.facility_id,
                    status__in=[
                        'approved',
                        'checked_in'
                    ],
                    start_time__lt=self.end_time,
                    end_time__gt=self.start_time
                )

                if conflicting_reservations.exists():
                    errors['start_time'] = (
                        'This closure conflicts with an approved '
                        'or checked-in reservation.'
                    )

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return (
            f'{self.facility.name} - '
            f'{self.start_time} to {self.end_time}'
        )