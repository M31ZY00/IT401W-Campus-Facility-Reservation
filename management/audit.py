from .models import AuditLog


def record_audit(request, action, instance, description=''):
    return AuditLog.objects.create(
        admin_user=request.user,
        action=action,
        model_name=instance.__class__.__name__,
        object_id=instance.pk,
        description=description
    )