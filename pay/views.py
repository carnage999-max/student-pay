import os
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework.decorators import action, api_view
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework import status
from django.http import FileResponse, JsonResponse
from .models import Payment, Transaction
from accounts.models import Department
from accounts.utils import get_bank_codes
from .serializers import PaymentSerializer, TransactionSerializer
from decouple import config
import requests
import json
from num2words import num2words
from receipt_utils.create_receipt import generate_receipt
from supabase_util import supabase


class PaymentViewSet(ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'delete']:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [AllowAny]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        department_id = self.kwargs.get("department_pk")
        print(Department.objects.get(pk=department_id))
        print(self.queryset.filter(department=Department.objects.get(pk=department_id)))
        if self.action == 'list':
            return self.queryset.filter(department=Department.objects.get(pk=department_id))
        return self.queryset
    
class TransactionViewSet(ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [IsAuthenticated]
        if self.action == 'update':
            permission_classes = [IsAdminUser]
        else:
            permission_classes = [AllowAny]
        return [permission() for permission in permission_classes]
    
    
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        first_name = serializer.validated_data['first_name']
        last_name = serializer.validated_data['last_name']
        email = serializer.validated_data['customer_email']
        department = Department.objects.get(id=int(request.data.get('department'))).id
        payment = Payment.objects.get(id=int(request.data.get('payment'))).id
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
                "callback_url": "http://localhost:3000/payment/pay/success"
            }
            #Initialize Paystack Transaction
            response = requests.post(url="https://api.paystack.co/transaction/initialize", headers=headers, data=json.dumps(txn_data)).json()
            authorization_url = response['data']['authorization_url']
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'authorization_url': authorization_url}, status=status.HTTP_200_OK)
    
    @action(methods=['GET'], detail=False, url_path='verify')
    def transaction_verify(self, request):
        reference = request.query_params.get('trxref')
        txn = Transaction.objects.filter(txn_reference=reference)
        if txn.exists():
            return Response({"receipt_url": self.get_serializer(txn.first()).data['receipt_url']}, status=status.HTTP_200_OK)
        else:
            headers = {
                    "Authorization": f"Bearer {config("PAYSTACK_SECRET_KEY")}",
                    "Content-Type": "application/json"
            }
            response = requests.get(f"https://api.paystack.co/transaction/verify/{reference}", headers=headers)
            response_data = response.json()
            metadata = response_data['data']['metadata']
            if response_data.get('status') and response_data['data']['status'] == 'success':
                txn_id = response_data['data']['id']
                txn_status = response_data['data']['status']
                amount_paid = response_data['data']['amount'] // 100
                ip_address = response_data['data']['ip_address']
                txn_reference = response_data['data']['reference']
                date_paid = response_data['data']['paid_at'].split("T")[0]
                first_name = metadata['first_name']
                last_name = metadata['last_name']
                received_from = f"{first_name} {last_name}"
                customer_email = metadata['email']
                customer_code = metadata['customer_code']
                payment = Payment.objects.get(id=metadata['payment_id'])
                department = Department.objects.get(id=metadata['department_id'])
                receipt_data = {
                    'header': department.dept_name.upper(), 
                    'date': date_paid,
                    'received_from': received_from,
                    "payment_for": payment.payment_for,
                    "amount_words": num2words(amount_paid * 100, to='currency', lang='en_NG'),
                    "amount": amount_paid,
                    "department_logo": department.logo_url,
                    "president_signature": department.president_signature_url,
                    "financial_signature": department.secretary_signature_url
                }
                transaction = Transaction.objects.create(
                    txn_id=txn_id, status=txn_status, amount_paid=amount_paid, ip_address=ip_address,
                    txn_reference=txn_reference, customer_code=customer_code, payment=payment,
                    department=department, received_from=received_from, first_name=first_name,
                    last_name=last_name, customer_email=customer_email
                )
                filename = f"{received_from.replace(' ', '_')}_{date_paid}.pdf"
                try:
                    pdf_stream = generate_receipt(data=receipt_data)
                    pdf_stream.seek(0)
                    supabase.storage.from_("receipts").upload(
                        path=filename,
                        file=pdf_stream.read(),
                        file_options={"content-type": "application/pdf", "upsert": 'true'}
                    )
                    
                    receipt_url = supabase.storage.from_("receipts").get_public_url(filename)
                    transaction.receipt_url = receipt_url
                    transaction.save()
                    # pdf_stream.seek(0)
                    # return FileResponse(pdf_stream, content_type="application/pdf", as_attachment=False, filename=filename)
                    return Response({"receipt_url": receipt_url}, status=status.HTTP_200_OK)
                except Exception as e:
                    return Response({"error": "Problem encountered creating receipt", 'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"error": "Transaction Failed"}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['GET'], url_path='stats', permission_classes=[IsAuthenticated])
    def transaction_stats(self, request):
        return Response({"e":4})
    
@api_view(['GET'])
def get_banks(request):
    banks = [{"name": bank_name, "code": bank_code} for bank_name, bank_code in get_bank_codes().items()]
    return JsonResponse(banks, safe=False)


        
