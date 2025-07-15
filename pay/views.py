from rest_framework.viewsets import ModelViewSet
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import status
from .models import Payment, Transaction
from accounts.models import Department
from .serializers import PaymentSerializer, TransactionSerializer
from decouple import config
import requests
import json


class PaymentViewSet(ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    
class TransactionViewSet(ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        first_name = serializer.validated_data['first_name']
        last_name = serializer.validated_data['last_name']
        email = serializer.validated_data['customer_email']
        department = (serializer.validated_data['department']).id
        payment = (serializer.validated_data['payment']).id
        try:
            metadata = dict()
            # Create Paystack Customer Instance
            headers = {
                "Authorization": f"Bearer {config("PAYSTACK_SECRET_KEY")}",
                "Content-Type": "application/json"
            }
            customer_info = {
                "email": email,
                "first_name": first_name,
                "last_name": last_name
            }
            response = requests.post(url="https://api.paystack.co/customer", headers=headers, data=json.dumps(customer_info)).json()
            customer_code = response['data']['customer_code']
            customer_info['customer_code'] = customer_code
            customer_info['payment_id'] = payment
            customer_info['department_id'] = department
            metadata.update(customer_info)
            amount_due = str(Payment.objects.get(id=payment).amount_due * 100)
            sub_account = Department.objects.get(id=department).sub_account_code
            txn_data = {
                "email": email,
                "amount": amount_due,
                "subaccount": sub_account,
                "bearer": "subaccount",
                "metadata": metadata,
                "callback_url": "http://localhost:8000/pay/pay/verify/"
            }
            print(txn_data)
            #Initialize Paystack Transaction
            response = requests.post(url="https://api.paystack.co/transaction/initialize", headers=headers, data=json.dumps(txn_data)).json()
            print(response)
            authorization_url = response['data']['authorization_url']
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'authorization_url': authorization_url}, status=status.HTTP_200_OK)
    
    @action(methods=['GET'], detail=False, url_path='verify')
    def transaction_verify(self, request):
        reference = request.query_params.get('trxref')
        headers = {
                "Authorization": f"Bearer {config("PAYSTACK_SECRET_KEY")}",
                "Content-Type": "application/json"
        }
        response = requests.get(f"https://api.paystack.co/transaction/verify/{reference}", headers=headers)
        response_data = response.json()
        print(response_data)
        metadata = response_data['data']['metadata']
        if response_data.get('status') and response_data['data']['status'] == 'success':
            txn_id = response_data['data']['id']
            txn_status = response_data['data']['status']
            amount_paid = response_data['data']['amount'] // 100
            ip_address = response_data['data']['ip_address']
            txn_reference = response_data['data']['reference']
            first_name = metadata['first_name']
            last_name = metadata['last_name']
            received_from = f"{first_name} {last_name}"
            customer_email = metadata['email']
            customer_code = metadata['customer_code']
            payment = Payment.objects.get(id=metadata['payment_id'])
            department = Department.objects.get(id=metadata['department_id'])
            transaction = Transaction.objects.create(
                txn_id=txn_id, status=txn_status, amount_paid=amount_paid, ip_address=ip_address,
                txn_reference=txn_reference, customer_code=customer_code, payment=payment,
                department=department, received_from=received_from, first_name=first_name,
                last_name=last_name, customer_email=customer_email
            )
            serializer = self.get_serializer(transaction)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response({"error": "Transaction Failed"}, status=status.HTTP_400_BAD_REQUEST)


        
