from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import (
    AuditLog,
    CAPAAction,
    CCVCriticalControlVerification,
    FLRA,
    FRA,
    Incident,
    JSA,
    JSAStep,
    MedicalAssessment,
    MedicalProfile,
    Objective,
    Observation,
    PTOChemicalHazardousSubstance,
    Reminder,
    SafetyChecklist,
    ScheduleItem,
    ToolboxTalk,
)

TRACKED_MODELS = (
    Incident,
    JSA,
    JSAStep,
    FRA,
    FLRA,
    Observation,
    PTOChemicalHazardousSubstance,
    CCVCriticalControlVerification,
    SafetyChecklist,
    ToolboxTalk,
    CAPAAction,
    ScheduleItem,
    Reminder,
    MedicalProfile,
    MedicalAssessment,
    Objective,
)


def _infer_actor(instance):
    for field in ('created_by', 'reported_by', 'performed_by', 'assessed_by', 'observed_by', 'owner', 'completed_by', 'conducted_by'):
        if hasattr(instance, field):
            user = getattr(instance, field)
            if user is not None:
                return user
    return None


def _tenant_site(instance):
    tenant = getattr(instance, 'tenant', None)
    site = getattr(instance, 'site', None)
    return tenant, site


@receiver(post_save)
def create_update_audit_log(sender, instance, created, **kwargs):
    if sender not in TRACKED_MODELS:
        return

    tenant, site = _tenant_site(instance)
    action = 'create' if created else 'update'

    AuditLog.objects.create(
        tenant=tenant,
        site=site,
        user=_infer_actor(instance),
        action=action,
        model_name=sender.__name__,
        object_id=str(instance.pk),
        object_repr=str(instance)[:255],
        change_summary=f'{sender.__name__} {action}d',
        payload={},
    )


@receiver(post_delete)
def delete_audit_log(sender, instance, **kwargs):
    if sender not in TRACKED_MODELS:
        return

    tenant, site = _tenant_site(instance)

    AuditLog.objects.create(
        tenant=tenant,
        site=site,
        user=_infer_actor(instance),
        action='delete',
        model_name=sender.__name__,
        object_id=str(instance.pk),
        object_repr=str(instance)[:255],
        change_summary=f'{sender.__name__} deleted',
        payload={},
    )
