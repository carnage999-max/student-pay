import csv
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from rest_framework.filters import OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.http import HttpResponse, JsonResponse
from django.conf import settings

# from pay.utils import send_receipt_email
from utils.fetchReceiptData import getReceiptData
from .filters import TransactionFilter
from utils.pagination import CustomResultsSetPagination
from pay.utils import send_receipt_email
from .paystack import Paystack
from .models import Payment, Transaction
from accounts.models import Department
from accounts.utils import get_bank_codes
from .serializers import PaymentSerializer, TransactionSerializer
from num2words import num2words
from receipt_utils.create_receipt import generate_receipt
from receipt_utils.upload_receipt import upload_receipt
import logging
import hashlib


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
        department = str(Department.objects.get(id=request.data.get("department")).id)
        payment = str(Payment.objects.get(id=request.data.get("payment")).id)
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
                "callback_url": (
                    "http://localhost:8000/pay/pay/verify/"
                    if settings.DEBUG
                    else "https://student-pay.sevalla.app/payment/pay/success/"
                ),
            }
            # Initialize Paystack Transaction
            authorization_url = paystack_obj.initiate_transaction(txn_data)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        logger.info("Transaction Initiated")
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
        """
        The `transaction_verify` function verifies a transaction, generates a receipt, and uploads it.

        :param request: The `transaction_verify` method is used to verify a transaction based on the
        provided `request` object. The `request` object contains query parameters that include a
        transaction reference (`trxref`)
        :return: The `transaction_verify` method returns a Response object containing either a receipt URL
        or an error message based on the outcome of the transaction verification process.
        """
        reference = request.query_params.get("trxref")
        txn = Transaction.objects.filter(txn_reference=reference)
        receipt_data = getReceiptData(reference)
        filename = f"{receipt_data['receipt_data']['payment_for'].replace(' ', '_')}_{receipt_data['receipt_data']['received_from']}.pdf"
        if "error" in receipt_data:
            logger.error(f"Error verifying Transaction")
            return Response(
                {
                    "error": "Error Verifying Transaction",
                    "detail": receipt_data["error"],
                }
            )
        if txn.exists():
            return Response(
                {"receipt_url": self.get_serializer(txn.first()).data["receipt_url"]},
                status=status.HTTP_200_OK,
            )
        else:
            # Verify transaction and get data for saving to db and for creating receipt
            transaction = Transaction.objects.create(**receipt_data["save_data"])
            try:
                # Receipt generation logic and error handling
                pdf_stream = generate_receipt(data=receipt_data["receipt_data"])
                pdf_stream.seek(0)

                receipt_url = upload_receipt(filename, pdf_stream)
                email_context = {
                    "header": receipt_data["receipt_data"]["header"],
                    "date": receipt_data["receipt_data"]["date"],
                    "received_from": receipt_data["receipt_data"]["received_from"],
                    "payment_for": receipt_data["receipt_data"]["payment_for"],
                    "amount": receipt_data["receipt_data"]["amount"],
                }
                try:
                    # sending receipt to customer email
                    send_receipt_email(
                        to_email=receipt_data["save_data"]["customer_email"],
                        context=email_context,
                        pdf_file=pdf_stream,
                        filename=filename,
                    )
                except Exception as e:
                    logger.error(f"Failed to trigger email thread: {str(e)}")
                if isinstance(receipt_url, dict) and "error" in receipt_url:
                    logger.error(f"Error uploading receipt: {receipt_url['detail']}")
                    return Response(
                        {
                            "error": "Error uploading receipt",
                            "detail": receipt_url["detail"],
                        },
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )
                logger.info(f"Receipt generated and uploaded: {receipt_url}")
                transaction.receipt_url = receipt_url
                transaction.save()
                return Response({"receipt_url": receipt_url}, status=status.HTTP_200_OK)
            except Exception as e:
                logger.error("Exception in receipt generation/upload:", str(e))
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


@api_view(["GET"])
def generate_receipt_with_reference(request):
    """
    This function generates a receipt with reference information for a transaction and uploads it as a
    PDF file.

    :param request: The code snippet you provided is a Django view function that generates a receipt for
    a transaction based on a provided reference. Here's a breakdown of the code:
    :return: The code snippet returns a JSON response containing the URL of the generated receipt if the
    transaction with the provided reference exists. If the transaction is found, it generates receipt
    data, creates a PDF receipt, uploads it, updates the transaction with the receipt URL, and returns
    the receipt URL in the JSON response.
    """
    reference = request.query_params.get("reference")
    transaction = Transaction.objects.filter(txn_reference=reference).first()
    if transaction:
        receipt_data = {
            "header": transaction.department.dept_name.upper(),
            "date": transaction.created_at.strftime("%Y-%m-%d"),
            "received_from": transaction.received_from,
            "payment_for": transaction.payment.payment_for,
            "amount_words": num2words(
                transaction.amount_paid * 100, to="currency", lang="en_NG"
            ),
            "amount": transaction.amount_paid,
            "department_logo": transaction.department.logo_url,
            "president_signature": transaction.department.president_signature_url,
            "financial_signature": transaction.department.secretary_signature_url,
        }
        try:
            pdf_stream = generate_receipt(data=receipt_data)
            pdf_stream.seek(0)
            filename = f"{transaction.received_from.replace(' ', '_')}_{transaction.created_at.strftime('%Y-%m-%d')}.pdf"
            receipt_url = upload_receipt(filename, pdf_stream)
            transaction.receipt_url = receipt_url
            transaction.save()
            logger.info(f"Receipt generated and uploaded: {receipt_url}")
            if isinstance(receipt_url, dict) and "error" in receipt_url:
                logger.error(f"Error uploading receipt: {receipt_url['detail']}")
                return Response(
                    {
                        "error": "Error uploading receipt",
                        "detail": receipt_url["detail"],
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
            return JsonResponse({"receipt_url": receipt_url}, status=200)
        except Exception as e:
            logger.error("Error generating receipt:", str(e))
            return Response(
                {"error": "Error generating receipt", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
    return Response(
        {"message": "Transaction not found"}, status=status.HTTP_404_NOT_FOUND
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def export_transactions_to_csv(request):
    """
    The function exports transactions data from a Django model to a CSV file and allows users to
    download the CSV file.

    :param request: The code snippet you provided is a Django view function that exports transactions
    data to a CSV file. It retrieves transaction data from the `Transaction` model and writes it to a
    CSV file for download
    :return: The code snippet provided is a Django view function that exports transactions data to a CSV
    file. When this view function is called with a GET request, it retrieves transaction data from the
    database, converts it to a CSV format, and returns a CSV file as a response for download.
    """
    transactions = Transaction.objects.filter(department=request.user).values(
        "txn_id",
        "status",
        "amount_paid",
        "txn_reference",
        "payment__payment_for",
        "department__dept_name",
        "received_from",
        "first_name",
        "last_name",
        "customer_email",
        "created_at",
    )

    if not transactions:
        return Response(
            {"message": "No transactions found"}, status=status.HTTP_404_NOT_FOUND
        )

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="transactions.csv"'

    writer = csv.writer(response)
    writer.writerow(transactions[0].keys())
    for transaction in transactions:
        writer.writerow(transaction.values())

    return response

@api_view(['GET'])
def verify_receipt(request):
    receipt_hash = request.query_params.get('hash')
    if not receipt_hash:
        return Response({'detail': "Missing Hash"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        txn = Transaction.objects.get(receipt_hash=receipt_hash)
        return Response({
            "status": "valid",
            "transaction_id": txn.txn_id,
            "amount": txn.amount_paid,
            "date": txn.created_at,
            "department": txn.department.dept_name
        })
    except Transaction.DoesNotExist:
        return Response({"status": "Invalid"}, status=status.HTTP_404_NOT_FOUND)
