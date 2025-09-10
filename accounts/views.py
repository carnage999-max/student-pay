from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from .models import Department
from .serializers import (
    RegisterDepartmentSerializer,
    LoginSerializer,
    DepartmentSerializer,
)
from utils.permissions import isVerifiedUser
from django.contrib.auth import authenticate


class RegisterViewSet(ModelViewSet):
    """
    This class defines a view set for registering a department with a POST request and generating access
    and refresh tokens upon successful registration.
    """

    http_method_names = ["post"]
    serializer_class = RegisterDepartmentSerializer
    queryset = Department.objects.all()

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            refresh = RefreshToken.for_user(serializer.instance)
            return Response(
                {
                    "access_token": str(refresh.access_token),
                    "refresh_token": str(refresh),
                    "department_id": serializer.instance.id,
                    "is_verified": serializer.instance.is_verified
                },
                status=status.HTTP_201_CREATED,
                headers=headers,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class LoginViewSet(ModelViewSet):
    """
    This class defines a view set for handling user login functionality in a Django REST framework API.
    """

    http_method_names = ["post"]
    serializer_class = LoginSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data.get("email")
        password = serializer.validated_data.get("password")
        user = authenticate(email=email, password=password)
        if user is None:
            return Response(
                {"error": "Email or Password is incorrect"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access_token": str(refresh.access_token),
                "refresh_token": str(refresh),
                "department_id": user.id,
                "is_verified": user.is_verified
            },
            status=status.HTTP_200_OK,
        )


class DepartmentViewSet(ModelViewSet):
    """
    The `DepartmentViewSet` class defines CRUD operations for Department objects with authentication,
    data validation, and external API interactions for creating subaccounts.
    """

    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [isVerifiedUser]
    http_method_names = ["get"]

    def get_permissions(self):
        if self.action in ["delete"]:
            permission_classes = [IsAuthenticated, isVerifiedUser]
        else:
            permission_classes = [AllowAny]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        if (
            self.action not in ["retrieve", "list"]
            or self.request.user.is_authenticated
        ):
            return self.queryset.filter(dept_name=self.request.user)
        else:
            return self.queryset.filter(is_verified=True)
