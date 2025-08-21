from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings


def send_receipt_email(to_email, context, pdf_file, filename="receipt.pdf"):
    """
    The function `send_receipt_email` sends an email with a payment receipt attached as a PDF file.
    
    :param to_email: The `to_email` parameter is the email address where you want to send the receipt
    email
    :param context: The `context` parameter in the `send_receipt_email` function is a dictionary that
    contains information related to the payment for which the receipt is being sent. It may include
    details such as the payment amount, date, transaction ID, customer name, and any other relevant
    information needed to generate the receipt and
    :param pdf_file: The `pdf_file` parameter in the `send_receipt_email` function is a file object that
    contains the PDF content of the receipt that you want to attach to the email. This file object
    should be opened in binary read mode ('rb') before passing it to the function. The function will
    attach this
    :param filename: The `filename` parameter in the `send_receipt_email` function is a string that
    represents the name of the PDF file that will be attached to the email. By default, if no value is
    provided for `filename`, it will be set to "receipt.pdf". This filename will be used when attaching,
    defaults to receipt.pdf (optional)
    """
    subject = f"Payment Receipt - {context.get('payment_for', '')}"
    from_email = settings.DEFAULT_FROM_EMAIL

    html_content = render_to_string("receipt_email.html", context)
    text_content = strip_tags(html_content)

    connection = get_connection(fail_silently=False)
    msg = EmailMultiAlternatives(
        subject, text_content, from_email, [to_email], connection=connection
    )
    msg.attach_alternative(html_content, "text/html")

    if pdf_file:
        msg.attach(filename, pdf_file.getvalue(), "application/pdf")

    msg.send()
