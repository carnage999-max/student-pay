from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PaymentViewSet, TransactionViewSet, get_banks


router = DefaultRouter()
# router.register('payment', PaymentViewSet, basename='payment')
router.register("pay", TransactionViewSet, basename="transaction")

urlpatterns = [
    path("", include(router.urls)),
    path("list-banks/", get_banks, name="list_banks"),
]
