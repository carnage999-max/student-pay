from django.dispatch import receiver
from django.db.models.signals import post_save
from .models import Department
import requests
from decouple import config



