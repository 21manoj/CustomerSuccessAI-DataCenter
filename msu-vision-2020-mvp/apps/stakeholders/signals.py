from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.stakeholders.models import UserStakeholderPersona
from apps.stakeholders.persona_utils import sync_primary_stakeholder_and_flag


@receiver(post_save, sender=UserStakeholderPersona)
def _after_persona_save(sender, instance, **kwargs):
    sync_primary_stakeholder_and_flag(instance.user_id)


@receiver(post_delete, sender=UserStakeholderPersona)
def _after_persona_delete(sender, instance, **kwargs):
    sync_primary_stakeholder_and_flag(instance.user_id)
