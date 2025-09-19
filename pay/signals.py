from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Payment


@receiver(post_save, sender=Payment)
def invalidate_payment_cache_on_save(sender, instance, **kwargs):
    cache.delete(
        f"payment_detail_{instance.pk}"
    )
    cache.delete("payment_list")


@receiver(post_delete, sender=Payment)
def invalidate_payment_cache_on_delete(sender, instance, **kwargs):
    cache.delete(f"payment_detail_{instance.pk}")
    cache.delete("payment_list")
