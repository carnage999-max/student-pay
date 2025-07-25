import requests
from decouple import config

def get_bank_codes():
    headers = {
    "Authorization": f"Bearer {config("PAYSTACK_SECRET_KEY")}"
}
    response = requests.get(url="https://api.paystack.co/bank", headers=headers)
    bank_codes = dict()
    for k in response.json()['data']:
        bank_codes[k['name']] = k['code']
    return bank_codes

def get_specific_bank_code(bank_name):
    return get_bank_codes()[bank_name]

def resolve_account_number(account_number, bank_code):
    header = {
        "Authorization": f"Bearer {config("PAYSTACK_SECRET_KEY")}"
    }
    response = requests.get(url=f"https://api.paystack.co/bank/resolve?account_number={account_number}&bank_code={bank_code}", headers=header)
    return response.json()['data']['account_name']
