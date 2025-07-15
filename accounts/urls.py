from django.urls import path, include
from .views import LoginViewSet, RegisterViewSet, DepartmentViewSet
from rest_framework.routers import DefaultRouter


router = DefaultRouter()
router.register('register', RegisterViewSet, basename='register')
router.register('login', LoginViewSet, basename='login')
router.register('department', DepartmentViewSet, basename='department')

urlpatterns = [
    path('', include(router.urls)),
]