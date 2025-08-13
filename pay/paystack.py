from decouple import config
import json
import requests


class Paystack:
    """
    A class to interact with the Paystack payment gateway API.

    Methods
    -------
    create_customer(data=None)
        Creates a new customer on Paystack using the provided data.

    initiate_transaction(data=None)
        Initiates a new transaction on Paystack with the given data.

    verify_transaction(txn_ref)
        Verifies the status of a transaction using its reference.
    """

    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {config('PAYSTACK_SECRET_KEY')}",
            "Content-Type": "application/json",
        }

    def create_customer(self, data=None):
        try:
            if data == None:
                return {"error": "cannot create customer - no data provided"}
            response = requests.post(
                url="https://api.paystack.co/customer",
                headers=self.headers,
                data=json.dumps(data),
            ).json()
            customer_code = response["data"]["customer_code"]
            return customer_code
        except Exception as e:
            return {"error": str(e)}

    def initiate_transaction(self, data=None):
        try:
            if data == None:
                return {"error": "cannot create transaction - no data provided"}
            response = requests.post(
                url="https://api.paystack.co/transaction/initialize",
                headers=self.headers,
                data=json.dumps(data),
            ).json()
            authorization_url = response["data"]["authorization_url"]
            return authorization_url
        except Exception as e:
            return {"error": str(e)}

    def verify_transaction(self, txn_ref):
        response = requests.get(
            f"https://api.paystack.co/transaction/verify/{txn_ref}",
            headers=self.headers,
        )
        try:
            response_data = response.json()
        except Exception as e:
            print("Paystack verify_transaction non-JSON response:", response.text)
            return {"error": f"Invalid response from Paystack: {str(e)}"}
        if response_data.get("status") and response_data["data"]["status"] == "success":
            metadata = response_data["data"]["metadata"]
            txn_id = response_data["data"]["id"]
            txn_status = response_data["data"]["status"]
            amount_paid = response_data["data"]["amount"] // 100
            ip_address = response_data["data"]["ip_address"]
            txn_reference = response_data["data"]["reference"]
            date_paid = response_data["data"]["paid_at"].split("T")[0]
            first_name = metadata["first_name"]
            last_name = metadata["last_name"]
            received_from = f"{first_name} {last_name}"
            customer_email = metadata["email"]
            customer_code = metadata["customer_code"]
            return {
                "txn_id": txn_id,
                "txn_status": txn_status,
                "amount_paid": amount_paid,
                "ip_address": ip_address,
                "txn_reference": txn_reference,
                "date_paid": date_paid,
                "received_from": received_from,
                "customer_email": customer_email,
                "customer_code": customer_code,
                "first_name": first_name,
                "last_name": last_name,
                "payment_id": metadata["payment_id"],
                "department_id": metadata["department_id"],
            }
        elif response_data.get(
            "code"
        ) == "transaction_not_found" and not response_data.get("status"):
            return {"error": "Transaction not found"}
        else:
            return {"error": "Unknown error from Paystack", "detail": response_data}
