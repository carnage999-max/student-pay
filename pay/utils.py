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
    contains information related to the payment for which the receipt is being sent.
    :param pdf_file: The `pdf_file` parameter in the `send_receipt_email` function is a file object that
    contains the PDF content of the receipt that you want to attach to the email.
    :param filename: The `filename` parameter in the `send_receipt_email` function is a string that
    represents the name of the PDF file that will be attached to the email.
    """
    subject = f"Payment Receipt - {context.get('payment_for', '')}"
    from_email = settings.DEFAULT_FROM_EMAIL

    html_content = render_to_string("receipt_email.html", context)
    text_content = strip_tags(html_content)

    msg = EmailMultiAlternatives(
        subject, text_content, from_email, [to_email]
    )
    msg.attach_alternative(html_content, "text/html")

    if pdf_file:
        msg.attach(filename, pdf_file.getvalue(), "application/pdf")

    msg.send()
    
    
def send_welcome_mail(to_email):
    """
    The function `send_welcome_mail` sends a welcome email to a specified email address using a
    predefined HTML template.
    
    :param to_email: The `to_email` parameter is the email address where you want to send the welcome
    email. It should be a string representing a valid email address.
    """
    subject = "Welcome to Student Pay"
    from_email = settings.DEFAULT_FROM_EMAIL

    html_content = render_to_string("welcome_email.html")
    text_content = strip_tags(html_content)

    msg = EmailMultiAlternatives(
        subject, text_content, from_email, [to_email]
    )
    msg.attach_alternative(html_content, "text/html")

    msg.send()
    
def send_approval_email(to_email, context):
    """
    The function `send_approval_email` sends an approval email to a specified email address using a
    predefined HTML template and context.
    
    :param to_email: The `to_email` parameter is the email address where you want to send the approval
    email. It should be a string representing a valid email address.
    :param context: The `context` parameter in the `send_approval_email` function is a dictionary that
    contains information related to the approval process. This context is used to populate the HTML
    template for the email.
    """
    subject = f"Department({context.get('dept_name', '')}) Approved - Student Pay"
    from_email = settings.DEFAULT_FROM_EMAIL

    html_content = render_to_string("account_verified.html", context)
    text_content = strip_tags(html_content)

    msg = EmailMultiAlternatives(
        subject, text_content, from_email, [to_email]
    )
    msg.attach_alternative(html_content, "text/html")

    msg.send()
    
def send_rejection_email(to_email, context):
    """
    The function `send_rejection_email` sends a rejection email to a specified email address using a
    predefined HTML template and context.
    
    :param to_email: The `to_email` parameter is the email address where you want to send the rejection
    email. It should be a string representing a valid email address.
    :param context: The `context` parameter in the `send_rejection_email` function is a dictionary that
    contains information related to the rejection process. This context is used to populate the HTML
    template for the email.
    """
    subject = f"Department({context.get('dept_name', '')}) Rejected - Student Pay"
    from_email = settings.DEFAULT_FROM_EMAIL

    html_content = render_to_string("account_rejected.html", context)
    text_content = strip_tags(html_content)
    
    print("Sending rejection email to:", to_email)

    msg = EmailMultiAlternatives(
        subject, text_content, from_email, [to_email]
    )
    msg.attach_alternative(html_content, "text/html")

    msg.send()
