import base64
from mailjet_rest import Client
from decouple import config
from django.conf import settings


api_key = config("MAILJET_API_KEY")
secret_key = config("MAILJET_SECRET_KEY")

mailjet = Client(auth=(api_key, secret_key), version="v3.1")


def send_receipt_email(to_email, pdf_file, variables, filename="receipt.pdf"):
    pdf_file_b64 = base64.b64encode(pdf_file.getvalue()).decode('utf-8')
    data = {
        "Messages": [
            {
                "From": {"Email": settings.MAILJET_SENDER_EMAIL, "Name": "Student Pay"},
                "To": [{"Email": to_email}],
                "TemplateID": 7288203,
                "TemplateLanguage": True,
                "Subject": "Your email flight plan!",
                'Variables': variables,
                "Attachments": [
                    {
                        "ContentType": "application/pdf",
                        "Filename": filename,
                        "Base64Content": pdf_file_b64,
                    }
                ],
            }
        ]
    }
    response = mailjet.send.create(data=data)
    print(response.status_code)
    print(response.json())
