from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractUser
from django.utils.translation import gettext_lazy as _


class CustomUserManager(BaseUserManager):
    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("The given email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self.db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        

        if extra_fields.get("is_staff") is not True:
            raise ValueError(
                "Superuser must have is_staff=True "
            )
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(
                "Superuser must have is_superuser=True"
            )

        return self._create_user(email, password, **extra_fields)
    
class Department(AbstractUser):
    email = models.EmailField(_("email address"), unique=True, error_messages={
        "unique": _("A user with that email already exists")
    })
    username = models.CharField(blank=True, null=True, default=None, max_length=10)
    dept_name = models.CharField(_("Department Name"), default="dept_name", max_length=50, null=True, blank=True)
    account_number = models.CharField(max_length=10, default="0000000000")
    bank_name = models.CharField(max_length=50, default="Bank Name")
    bank_code = models.CharField(max_length=10, default="000")
    account_name = models.CharField(_("Account Name"), max_length=200, default="XXXXXXXXXX")
    sub_account_code = models.CharField(_("Sub Account"), max_length=20, default="XXXXXXXXXXXX")
    logo_url = models.CharField(_("Link to Logo"), max_length=200, null=True, blank=True)
    president_signature_url = models.CharField(_("Link to President Signature"), max_length=200, null=True, blank=True)
    secretary_signature_url = models.CharField(_("Link to Financial Secretary Signature"), max_length=200, null=True, blank=True)
    
    
    
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    
    def __str__(self):
        return self.dept_name

    objects = CustomUserManager()
