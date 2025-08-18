from rest_framework.serializers import ModelSerializer, CharField, EmailField
from .models import Payment, Transaction


class PaymentSerializer(ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'payment_for', 'amount_due', 'created_at']
        read_only_fields = ['id', 'created_at']
        
    def create(self, validated_data):
        department = self.context['request'].user
        return Payment.objects.create(department=department, **validated_data)


class TransactionSerializer(ModelSerializer):
    payment_for = CharField(source="payment.payment_for", read_only=True)

    class Meta:
        model = Transaction
        fields = [
            "txn_id",
            "department",
            "payment",
            "amount_paid",
            "customer_code",
            "received_from",
            "status",
            "created_at",
            "first_name",
            "last_name",
            "customer_email",
            "receipt_url",
            "payment_for",
        ]
        read_only_fields = [
            "txn_id",
            "received_from",
            "created_at",
            "customer_code",
            "status",
            "amount_paid",
            "receipt_url",
            "payment_for",
        ]
