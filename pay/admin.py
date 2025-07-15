from django.contrib import admin
from .models import Transaction, Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['department', 'payment_for', 'amount_due']
    
@admin.register(Transaction)    
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['txn_id', 'department', 'payment', 'amount_paid', 'status']
    list_filter = ['status', 'department']
