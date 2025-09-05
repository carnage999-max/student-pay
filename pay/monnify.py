import requests
from decouple import config
from pprint import pprint
from base64 import standard_b64encode
from django.conf import settings
import uuid
import json


def generateAccessToken():
    auth_url = f"{config('MONNIFY_BASE_URL')}/api/v1/auth/login"
    token_str = config("MONNIFY_API_KEY") + ":" + config("MONNIFY_SECRET_KEY")
    token = standard_b64encode(token_str.encode("ascii")).decode("ascii")
    auth_headers = {"Authorization": f"Basic {token}"}
    auth_res = requests.post(auth_url, headers=auth_headers).json()
    pprint(auth_res["responseBody"]["accessToken"])
    return auth_res["responseBody"]["accessToken"]


def generateUniqueTransactionRef():
    """
    The function generates a unique transaction reference using a UUID.
    :return: A unique transaction reference is being returned as a string.
    """
    return str(uuid.uuid4())


txn_data = {
    "amount": 6000,
    "customerName": "Stephen Ikooohane",
    "customerEmail": "stephen@lopoikhane.com",
    "paymentReference": "Food 91010001011",
    "paymentDescription": "Trial transactionizationaticalous",
}


class MonnifyException(Exception):
    """
    The class `MonnifyTransactionInitFailed` defines a custom exception for unexpected errors during
    Monnify transaction initialization.
    """

    def __init__(self, message="An unexpected custom error occurred"):
        self.message = message
        super().__init__(self.message)


class Monnify:
    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {generateAccessToken()}",
            "Content-Type": "application/json",
        }
        self.currencyCode = "NGN"

    def getBanks(self):
        """
        The function `getBanks` retrieves a list of banks from an API and returns a dictionary mapping
        bank names to their corresponding codes.
        :return: A dictionary containing the names of banks as keys and their corresponding codes as
        values.
        """
        response = requests.get(
            f"{config('MONNIFY_BASE_URL')}/api/v1/banks", headers=self.headers
        ).json()
        if not response["requestSuccessful"] or response["responseCode"] == "99":
            raise MonnifyException(message=response["responseMessage"])
        banks = {}
        for k in response["responseBody"]:
            banks[k["name"]] = k["code"]
        return banks

    def createSubAccount(self, data):
        data[0]["currencyCode"] = self.currencyCode
        pprint(data)
        response = requests.post(
            f"{config('MONNIFY_BASE_URL')}/api/v1/sub-accounts/",
            headers=self.headers,
            json=data,
        ).json()
        if not response["requestSuccessful"] or response["responseCode"] == "99":
            raise MonnifyException(message=response["responseMessage"])
        return response

    def initializeTransaction(self, data):
        """
        The function `initializeTransaction` initializes a transaction by setting certain data fields,
        making a POST request to a specified URL, and handling the response.

        :param data: The `initializeTransaction` method takes in a `data` parameter and performs the
        following actions:
        :return: The method is returning the checkout URL from the response body of a transaction
        initialization request made to the Monnify API.
        """
        data["contractCode"] = config("CONTRACT_CODE")
        data["redirectUrl"] = config("PROD_CALLBACK_URL")
        data["currencyCode"] = self.currencyCode
        # data['redirectUrl'] = f'{config('DEV_CALLBACK_URL')}' if settings.DEBUG else f'{config('PROD_CALLBACK_URL')}'
        pprint(f"data: {json.dumps(data)}")
        txn_url = f"{config('MONNIFY_BASE_URL')}/api/v1/merchant/transactions/init-transaction"
        response = requests.post(
            txn_url, data=json.dumps(data), headers=self.headers
        ).json()
        if not response["requestSuccessful"] or response["responseCode"] == "99":
            raise MonnifyException(message=response["responseMessage"])
        return response["responseBody"]["checkoutUrl"]


p = Monnify()
pprint("--------transaction init------")
pprint(p.getBanks())

subacc_dta = [
	{
		"bankCode": "090272",
		"accountNumber": "1100020577",
		"email": "test@gmail.com",
		"defaultSplitPercentage": 94.7
	}
]
pprint(p.initializeTransaction(txn_data))
