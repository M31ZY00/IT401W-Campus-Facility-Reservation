from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('ARCHIVE', 'Archive'),
        ('REACTIVATE', 'Reactivate'),
        ('APPROVE', 'Approve'),
        ('REJECT', 'Reject'),
        ('CANCEL', 'Cancel'),
        ('CHECK_IN', 'Check In'),
        ('COMPLETE', 'Complete'),
        ('NO_SHOW', 'No Show'),
        ('OTHER', 'Other'),
    ]

    admin_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='admin_audit_logs'
    )

    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES
    )

    model_name = models.CharField(max_length=100)

    object_id = models.PositiveBigIntegerField()

    description = models.TextField(blank=True)

    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return (
            f'{self.admin_user.username} - '
            f'{self.action} - '
            f'{self.model_name} #{self.object_id}'
        )

class SystemSetting(models.Model):
    max_booking_hours = models.PositiveSmallIntegerField(
        default=4,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(24)
        ]
    )

    advance_booking_days = models.PositiveSmallIntegerField(
        default=30,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(365)
        ]
    )

    updated_at = models.DateTimeField(auto_now=True)

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='system_settings_updates'
    )

    @classmethod
    def get_current(cls):
        instance, created = cls.objects.get_or_create(
            pk=1,
            defaults={
                'max_booking_hours': 4,
                'advance_booking_days': 30
            }
        )

        return instance

    def __str__(self):
        return 'System Settings'