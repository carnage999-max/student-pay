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
        """
        The `create_customer` function sends a POST request to create a customer using the Paystack API and
        returns the customer code if successful.

        :param data: The `data` parameter in the `create_customer` method is used to pass the information
        required to create a customer. This information typically includes details such as the customer's
        name, email, phone number, and other relevant details needed to create a customer profile in the
        system. The `data` parameter
        :return: If the `data` parameter is `None`, the function will return `{"error": "cannot create
        customer - no data provided"}`. Otherwise, it will make a POST request to the Paystack API to create
        a customer using the provided data. If successful, it will return the customer code. If an exception
        occurs during the process, it will return `{"error": <error_message>}`
        """
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
        """
        The function `initiate_transaction` sends a POST request to the Paystack API to initialize a
        transaction and returns the authorization URL.

        :param data: The `data` parameter in the `initiate_transaction` method is used to provide the
        necessary information required to initialize a transaction. This data typically includes details
        such as the amount to be transacted, the email of the customer, and any other relevant
        information needed to process the transaction
        :return: If the `initiate_transaction` method is successful, it will return the authorization
        URL for the transaction. If there is an error or an exception occurs during the process, it will
        return a dictionary with an "error" key containing a description of the error.
        """
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
        """
        The `verify_transaction` function in Python verifies a transaction with Paystack API and returns
        relevant transaction details or error messages.

        :param txn_ref: The `txn_ref` parameter in the `verify_transaction` method is the transaction
        reference that is used to identify a specific transaction in the Paystack API. It is passed to the
        API endpoint to retrieve information about a particular transaction and verify its status
        :return: The `verify_transaction` method returns a dictionary containing various transaction details
        if the transaction is successfully verified. If the transaction status is "success", it extracts and
        returns specific information such as transaction ID, status, amount paid, IP address, reference,
        date paid, customer details, and metadata.
        """
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
