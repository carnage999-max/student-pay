from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import action
from .models import Department
from .serializers import (
    RegisterDepartmentSerializer,
    LoginSerializer,
    DepartmentSerializer,
)
from django.contrib.auth import authenticate
from .utils import get_specific_bank_code, resolve_account_number
from decouple import config
import requests
from io import BytesIO
from supabase_util import supabase


class RegisterViewSet(ModelViewSet):
    """
    This class defines a view set for registering a department with a POST request and generating access
    and refresh tokens upon successful registration.
    """

    http_method_names = ["post"]
    serializer_class = RegisterDepartmentSerializer
    queryset = Department.objects.all()

    def create(self, request, *args, **kwargs):
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
            },
            status=status.HTTP_200_OK,
            headers=headers,
        )


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
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ["delete", "update", "partial_update"]:
            permission_classes = [IsAuthenticated]
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
            return self.queryset

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        bank_name = serializer.validated_data.get("bank_name")
        account_number = serializer.validated_data.get("account_number")
        logo = request.FILES.get("logo")
        president_signature = request.FILES.get("president_signature_url")
        secretary_signature = request.FILES.get("secretary_signature_url")
        try:
            bank_code = get_specific_bank_code(bank_name)
            account_name = resolve_account_number(account_number, bank_code)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        instance.bank_code = bank_code
        instance.account_name = account_name

        url = "https://api.paystack.co/subaccount"
        headers = {
            "Authorization": f"Bearer {config('PAYSTACK_SECRET_KEY')}",
            "content_type": "application/json",
        }
        data = {
            "business_name": instance.dept_name,
            "settlement_bank": bank_code,
            "account_number": account_number,
            "percentage_charge": 0,
        }
        response = requests.post(url=url, headers=headers, data=data)
        # Upload Image files to supabase

        # Upload logo if present
        if logo:
            supabase.storage.from_("logo").upload(
                path=logo.name, file=logo.read(), file_options={"upsert": "true"}
            )
            instance.logo_url = supabase.storage.from_("logo").get_public_url(logo.name)

        # Upload president signature if present
        if president_signature:
            supabase.storage.from_("signatures").upload(
                path=president_signature.name,
                file=president_signature.read(),
                file_options={"upsert": "true"},
            )
            instance.president_signature_url = supabase.storage.from_(
                "signatures"
            ).get_public_url(president_signature.name)
        # Upload secretary signature if present
        if secretary_signature:
            supabase.storage.from_("signatures").upload(
                path=secretary_signature.name,
                file=secretary_signature.read(),
                file_options={"upsert": "true"},
            )
            instance.secretary_signature_url = supabase.storage.from_(
                "signatures"
            ).get_public_url(secretary_signature.name)
        instance.sub_account_code = response.json()["data"]["subaccount_code"]
        self.perform_update(serializer)
        return Response(serializer.data, status=status.HTTP_200_OK)
