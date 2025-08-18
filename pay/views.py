from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework.decorators import action, api_view
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from rest_framework.filters import OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.http import JsonResponse
from .filters import TransactionFilter
from .pagination import CustomResultsSetPagination
from .paystack import Paystack
from .models import Payment, Transaction
from accounts.models import Department
from accounts.utils import get_bank_codes
from .serializers import PaymentSerializer, TransactionSerializer
from decouple import config
import requests
from num2words import num2words
from receipt_utils.create_receipt import generate_receipt
from supabase_util import supabase
import logging


logger = logging.getLogger(__name__)


class PaymentViewSet(ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ["create", "update", "delete"]:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [AllowAny]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        department_id = self.kwargs.get("department_pk")
        if self.action == "list":
            return self.queryset.filter(
                department=Department.objects.get(pk=department_id)
            )
        return self.queryset


class TransactionViewSet(ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    http_method_names = ["post", "get"]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = TransactionFilter
    ordering_fields = ["created_at"]
    pagination_class = CustomResultsSetPagination

    def get_queryset(self):
        if self.action == "list" and self.request.user.is_authenticated:
            return self.queryset.filter(department=self.request.user).order_by(
                "-created_at"
            )
        return super().get_queryset()

    def get_permissions(self):
        if self.action in ["transaction_stats", "list", "retrieve"]:
            permission_classes = [IsAuthenticated]
        elif self.action in ["transaction_verify", "create"]:
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        first_name = serializer.validated_data["first_name"]
        last_name = serializer.validated_data["last_name"]
        email = serializer.validated_data["customer_email"]
        department = Department.objects.get(id=int(request.data.get("department"))).id
        payment = Payment.objects.get(id=int(request.data.get("payment"))).id
        try:
            metadata = dict()
            customer_info = {
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
            }
            paystack_obj = Paystack()
            customer_code = paystack_obj.create_customer(customer_info)
            customer_info["customer_code"] = customer_code
            customer_info["payment_id"] = payment
            customer_info["department_id"] = department
            metadata.update(customer_info)
            amount_due = str(Payment.objects.get(id=payment).amount_due * 100)
            sub_account = Department.objects.get(id=department).sub_account_code
            txn_data = {
                "email": email,
                "amount": amount_due,
                "subaccount": sub_account,
                "bearer": "subaccount",
                "metadata": metadata,
                "callback_url": "http://localhost:3000/payment/pay/success/",
            }
            # Initialize Paystack Transaction
            authorization_url = paystack_obj.initiate_transaction(txn_data)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {"authorization_url": authorization_url}, status=status.HTTP_200_OK
        )

    @action(
        methods=["GET"],
        detail=False,
        url_path="verify",
        pagination_class=None,
        permission_classes=[AllowAny],
    )
    def transaction_verify(self, request):
        reference = request.query_params.get("trxref")
        txn = Transaction.objects.filter(txn_reference=reference)
        if txn.exists():
            return Response(
                {"receipt_url": self.get_serializer(txn.first()).data["receipt_url"]},
                status=status.HTTP_200_OK,
            )
        else:
            paystack_obj = Paystack()
            transaction_data = paystack_obj.verify_transaction(reference)
            if "error" in transaction_data:
                return Response(
                    {"error": transaction_data["error"]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            payment = Payment.objects.get(id=transaction_data["payment_id"])
            department = Department.objects.get(id=transaction_data["department_id"])
            receipt_data = {
                "header": department.dept_name.upper(),
                "date": transaction_data["date_paid"],
                "received_from": transaction_data["received_from"],
                "payment_for": payment.payment_for,
                "amount_words": num2words(
                    transaction_data["amount_paid"] * 100, to="currency", lang="en_NG"
                ),
                "amount": transaction_data["amount_paid"],
                "department_logo": department.logo_url,
                "president_signature": department.president_signature_url,
                "financial_signature": department.secretary_signature_url,
            }
            print(receipt_data)
            transaction = Transaction.objects.create(
                txn_id=transaction_data["txn_id"],
                status=transaction_data["txn_status"],
                amount_paid=transaction_data["amount_paid"],
                ip_address=transaction_data["ip_address"],
                txn_reference=transaction_data["txn_reference"],
                customer_code=transaction_data["customer_code"],
                payment=payment,
                department=department,
                received_from=transaction_data["received_from"],
                first_name=transaction_data["first_name"],
                last_name=transaction_data["last_name"],
                customer_email=transaction_data["customer_email"],
            )
            filename = f"{transaction_data['received_from'].replace(' ', '_')}_{transaction_data['date_paid']}.pdf"
            try:
                pdf_stream = generate_receipt(data=receipt_data)
                pdf_stream.seek(0)

                try:
                    # Use requests to upload the file directly from memory
                    headers = {
                        "apikey": config("SUPABASE_KEY"),
                        "Authorization": f"Bearer {config('SUPABASE_KEY')}",
                        "Content-Type": "application/pdf",
                        "x-upsert": "true",
                    }
                    url = f"{config('SUPABASE_URL')}/storage/v1/object/receipts/{filename}"

                    response = requests.post(
                        url, headers=headers, data=pdf_stream.read()
                    )
                    response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)

                    print(f"Successfully uploaded {filename} to Supabase.")

                except requests.exceptions.RequestException as e:
                    if e.response is not None:
                        print(f"Response status: {e.response.status_code}")
                        print(f"Response text: {e.response.text}")
                    raise

                receipt_url = supabase.storage.from_("receipts").get_public_url(
                    filename
                )
                transaction.receipt_url = receipt_url
                transaction.save()
                return Response({"receipt_url": receipt_url}, status=status.HTTP_200_OK)
            except Exception as e:
                print("Exception in receipt generation/upload:", str(e))
                return Response(
                    {
                        "error": "Problem encountered creating receipt",
                        "detail": str(e),
                        "code": "receipt_generation_error",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

    @action(
        detail=False,
        methods=["GET"],
        url_path="stats",
        permission_classes=[IsAuthenticated],
    )
    def transaction_stats(self, request):
        transactions = self.queryset.filter(department=request.user).order_by(
            "-created_at"
        )
        payments = Payment.objects.filter(department=request.user)
        total_payments = payments.count()
        if not transactions.exists():
            return Response(
                {"message": "No transactions found for this department"},
                status=status.HTTP_404_NOT_FOUND,
            )
        total_amount = sum(txn.amount_paid for txn in transactions)
        total_transactions = transactions.count()

        stats = {
            "total_amount": total_amount,
            "total_transactions": total_transactions,
            "total_payments": total_payments,
        }
        return Response(stats, status=status.HTTP_200_OK)


@api_view(["GET"])
def get_banks(request):
    """
    The function `get_banks` retrieves a list of banks with their corresponding codes and returns them
    as a JSON response.

    :param request: The `request` parameter in the `get_banks` function is an object that contains
    information about the current HTTP request.
    :return: A list of dictionaries containing the names and codes of banks is being returned in JSON
    format.
    """
    banks = [
        {"name": bank_name, "code": bank_code}
        for bank_name, bank_code in get_bank_codes().items()
    ]
    return JsonResponse(banks, safe=False)
