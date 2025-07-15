from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Department
from .serializers import RegisterDepartmentSerializer, LoginSerializer, DepartmentSerializer
from django.contrib.auth import authenticate
from .utils import get_specific_bank_code, resolve_account_number
from decouple import config
import requests


class RegisterViewSet(ModelViewSet):
    http_method_names = ['post']
    serializer_class = RegisterDepartmentSerializer
    queryset = Department.objects.all()
    
class LoginViewSet(ModelViewSet):
    http_method_names = ['post']
    serializer_class = LoginSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data.get("email")
        password = serializer.validated_data.get('password')
        user = authenticate(email=email, password=password)
        if user is None:
            return Response({'error': 'Email or Password is incorrect'}, status=status.HTTP_401_UNAUTHORIZED)
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access_token": str(refresh.access_token),
                "refresh_token": str(refresh)
            }, status=status.HTTP_200_OK
        )
        
class DepartmentViewSet(ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        bank_name = serializer.validated_data.get('bank_name')
        account_number = serializer.validated_data.get('account_number')
        try:
            bank_code = get_specific_bank_code(bank_name)
            account_name = resolve_account_number(account_number, bank_code)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        instance.bank_code = bank_code
        instance.account_name = account_name
        
        url="https://api.paystack.co/subaccount"
        headers = {
            'Authorization': f"Bearer {config('PAYSTACK_SECRET_KEY')}",
            'content_type': "application/json"
        }
        data={ 
            "business_name": instance.dept_name, 
            "settlement_bank": bank_code,
            "account_number": account_number, 
            "percentage_charge": 0,
        }
        response = requests.post(url=url, headers=headers, data=data)
        print(response.json())
        instance.sub_account_code = response.json()['data']['subaccount_code']
        self.perform_update(serializer)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
        

