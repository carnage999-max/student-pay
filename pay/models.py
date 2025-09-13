from django.db import models
from django.utils.translation import gettext_lazy as _


class Payment(models.Model):
    department = models.ForeignKey(
        "accounts.Department", on_delete=models.CASCADE, related_name="dept_payment"
    )
    payment_for = models.CharField(_("Payment For"), max_length=50, default="Fee")
    amount_due = models.DecimalField(
        _("Amount Expected"), decimal_places=2, max_digits=6
    )
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)

    def __str__(self):
        return self.payment_for


class Transaction(models.Model):
    txn_id = models.BigAutoField(_("Transaction ID"), primary_key=True)
    department = models.ForeignKey(
        "accounts.Department",
        on_delete=models.SET_NULL,
        null=True,
        related_name="dept_txn",
    )
    payment = models.ForeignKey(
        "pay.Payment", on_delete=models.SET_NULL, null=True, related_name="payment_txn"
    )
    amount_paid = models.DecimalField(_("Amount Paid"), decimal_places=2, max_digits=6)
    created_at = models.DateTimeField(_("Transaction Created Date"), auto_now_add=True)
    status = models.CharField(
        _("Transaction Status"), max_length=20, null=True, blank=True
    )
    customer_code = models.CharField(_("Customer Code"), max_length=20, null=True)
    first_name = models.CharField(_("First Name"), max_length=20, null=True)
    last_name = models.CharField(_("Last Name"), max_length=20, null=True)
    customer_email = models.EmailField(
        _("Customer E-mail"), default="customer@email.com"
    )
    received_from = models.CharField(_("Received From"), max_length=50)
    ip_address = models.CharField(_("IP Address"), max_length=20, null=True)
    txn_reference = models.CharField(
        _("Transaction Reference"), max_length=15, db_index=True
    )
    receipt_url = models.CharField(
        _("Receipt URL"), max_length=200, null=True, blank=True
    )
    receipt_hash = models.CharField(_("Receipt Hash"), max_length=64, unique=True, editable=False)


    def __str__(self):
        return self.received_from
