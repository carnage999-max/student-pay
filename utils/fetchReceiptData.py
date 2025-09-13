from pay.models import Transaction, Payment
from pay.paystack import Paystack
from accounts.models import Department
from num2words import num2words
import hashlib


def getReceiptData(tx_ref: str):
    """
    The function `getReceiptData` retrieves transaction data, verifies it, and generates receipt
    information based on the transaction details.
    
    :param tx_ref: `tx_ref` is a reference to a transaction. It is used to identify and retrieve
    specific transaction data
    :type tx_ref: str
    :return: The `getReceiptData` function returns a dictionary containing two main keys: "receipt_data"
    and "save_data".
    """
    paystack_obj = Paystack()
    transaction_data = paystack_obj.verify_transaction(tx_ref)
    print("transaction data", transaction_data)
    payment = Payment.objects.get(id=transaction_data["payment_id"])
    department = Department.objects.get(id=transaction_data["department_id"])
    raw_string = f"{transaction_data['customer_email']}{transaction_data['date_paid']}{transaction_data['txn_id']}"
    receipt_hash = hashlib.sha256(raw_string.encode()).hexdigest()
    if "error" in transaction_data:
        return {"error": transaction_data["error"]}
    response = {
        "receipt_data": {
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
            "receipt_hash": receipt_hash,
        },
        "save_data": {
            "txn_id": transaction_data["txn_id"],
            "status": transaction_data["txn_status"],
            "ip_address": transaction_data["ip_address"],
            "amount_paid": transaction_data["amount_paid"],
            "txn_reference": transaction_data["txn_reference"],
            "customer_code": transaction_data["customer_code"],
            "received_from": transaction_data["received_from"],
            "payment": payment,
            "department": department,
            "first_name": transaction_data["first_name"],
            "last_name": transaction_data["last_name"],
            "customer_email": transaction_data["customer_email"],
            "receipt_hash": receipt_hash,
        },
    }
    return response
