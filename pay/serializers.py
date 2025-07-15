from rest_framework.serializers import ModelSerializer, CharField, EmailField
from .models import Payment, Transaction


class PaymentSerializer(ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"
        
class TransactionSerializer(ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['txn_id', 'department', 'payment', 'amount_paid', 'customer_code', 'received_from', 'status', 'created_at', 'first_name', 'last_name', 'customer_email']
        read_only_fields = ['txn_id', 'received_from', 'created_at', 'customer_code', 'status', 'amount_paid']