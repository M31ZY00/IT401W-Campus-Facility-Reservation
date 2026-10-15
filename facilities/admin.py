from django.contrib import admin
from .models import Facility, FacilityCategory, Amenity, FacilityClosure


@admin.register(FacilityCategory)
class FacilityCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)


@admin.register(Amenity)
class AmenityAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)


@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'category',
        'location',
        'capacity',
        'is_active',
    )

    list_filter = ('category', 'is_active')
    search_fields = ('name', 'location')
    filter_horizontal = ('amenities',)


@admin.register(FacilityClosure)
class FacilityClosureAdmin(admin.ModelAdmin):
    list_display = (
        'facility',
        'start_time',
        'end_time',
        'reason',
    )

    list_filter = ('facility',)
    search_fields = ('facility__name', 'reason')
    readonly_fields = ('created_at',)