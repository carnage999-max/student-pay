from django.db.models.signals import post_save
from django.dispatch import receiver
from pay.utils import send_welcome_mail
from accounts.models import Department
import logging


logger = logging.getLogger(__name__)

@receiver(post_save, sender=Department)
def send_welcome_email_signal(sender, instance, created, **kwargs):
    if created:
        send_welcome_mail(instance.email)
        logger.info("Email sent!")
        