# jobcards/signals.py
from django.contrib.auth import get_user_model
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.db import transaction

from jobcards.utils.account_email import send_profile_change_password_email

User = get_user_model()

@receiver(pre_save, sender=User)
def _mark_email_changed(sender, instance, **kwargs):
    # True se o e-mail mudou de fato (valor diferente do que estava no banco)
    if not instance.pk:
        instance._email_changed_now = bool((instance.email or "").strip())
        return
    try:
        old = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        instance._email_changed_now = bool((instance.email or "").strip())
        return
    instance._email_changed_now = ((old.email or "").strip() != (instance.email or "").strip())

@receiver(post_save, sender=User)
def _send_on_create_or_email_change(sender, instance: User, created, **kwargs):
    # (a) Usuário novo com e-mail
    if created and instance.email:
        transaction.on_commit(lambda: send_profile_change_password_email(instance))
        return
    # (b) E-mail foi alterado (para outro endereço)
    if not created and getattr(instance, "_email_changed_now", False) and instance.email:
        transaction.on_commit(lambda: send_profile_change_password_email(instance))
