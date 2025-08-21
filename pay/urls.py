from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TransactionViewSet, get_banks, generate_receipt_with_reference, export_transactions_to_csv


router = DefaultRouter()
router.register("pay", TransactionViewSet, basename="transaction")

urlpatterns = [
    path("", include(router.urls)),
    path("list-banks/", get_banks, name="list_banks"),
    path("generate-receipt/", generate_receipt_with_reference, name="generate_receipt"),
    path('export-transactions/', export_transactions_to_csv, name='export_transactions'),
]
