from django.urls import path, include
from .views import LoginViewSet, RegisterViewSet, DepartmentViewSet
from rest_framework.routers import DefaultRouter
from pay.views import PaymentViewSet
from rest_framework_nested.routers import NestedDefaultRouter


router = DefaultRouter()
router.register("register", RegisterViewSet, basename="register")
router.register("login", LoginViewSet, basename="login")
router.register("department", DepartmentViewSet, basename="department")

department_router = NestedDefaultRouter(router, "department", lookup="department")
department_router.register("payment", PaymentViewSet, basename="payments")

urlpatterns = [
    path("", include(router.urls)),
    path("", include(department_router.urls)),
]
