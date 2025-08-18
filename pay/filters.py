from .models import Transaction
from django_filters.rest_framework import FilterSet, CharFilter


class TransactionFilter(FilterSet):
    payment_for = CharFilter(field_name="payment__payment_for", lookup_expr="icontains")

    class Meta:
        model = Transaction
        fields = {
            "received_from": ["exact", "icontains"],
            "status": ["exact"],
        }
