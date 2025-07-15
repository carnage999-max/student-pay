from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PaymentViewSet, TransactionViewSet


router = DefaultRouter()
router.register('payment', PaymentViewSet, basename='payment')
router.register('pay', TransactionViewSet, basename='transaction')

urlpatterns = [
    path('', include(router.urls)),
]

