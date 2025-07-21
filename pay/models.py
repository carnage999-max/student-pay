from django.db import models
from django.utils.translation import gettext_lazy as _


class Payment(models.Model):
    department = models.ForeignKey("accounts.Department", on_delete=models.CASCADE, related_name='dept_payment')
    payment_for = models.CharField(_("Payment For"), max_length=50, default="Fee")
    amount_due = models.DecimalField(_("Amount Expected"), decimal_places=2, max_digits=6)
    
    def __str__(self):
        return self.payment_for
    
class Transaction(models.Model):
    txn_id = models.BigAutoField(_("Transaction ID"), primary_key=True)
    department = models.ForeignKey("accounts.Department", on_delete=models.SET_NULL, null=True, related_name='dept_txn')
    payment = models.ForeignKey("pay.Payment", on_delete=models.SET_NULL, null=True, related_name='payment_txn')
    amount_paid = models.DecimalField(_("Amount Paid"), decimal_places=2, max_digits=6)
    created_at = models.DateTimeField(_("Transaction Created Date"), auto_now_add=True)
    status = models.CharField(_("Transaction Status"), max_length=20, null=True, blank=True)
    customer_code = models.CharField(_("Customer Code"), max_length=20, default="XXXXXXXXXXXXXX")
    first_name = models.CharField(_("First Name"), max_length=20, default="XXXXXXXXXXXXXX")
    last_name = models.CharField(_("Last Name"), max_length=20, default="XXXXXXXXXXXXXX")
    customer_email = models.EmailField(_("Customer E-mail"), default="customer@email.com")
    received_from = models.CharField(_("Received From"), max_length=50, default="XXXXXXXXXXXXXX")
    ip_address = models.CharField(_("IP Address"), max_length=20, default="XXXXXXXXXXX")
    txn_reference = models.CharField(_("Transaction Reference"), max_length=15, default="XXXXXXXXXXXXX" )
    receipt_url = models.CharField(_("Receipt URL"), max_length=200, default="XXXXXXXXXXXXX", null=True, blank=True)
    
    def __str__(self):
        return self.received_from
    
    
