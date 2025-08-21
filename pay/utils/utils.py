import threading
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags


def _send_mail(to_email, context, pdf_file, filename):
    subject = f"Payment Receipt - {context.get('payment_for', '')}"
    from_email = "noreply@yourdomain.com"

    html_content = render_to_string("receipt_email.html", context)
    text_content = strip_tags(html_content)

    msg = EmailMultiAlternatives(subject, text_content, from_email, [to_email])
    msg.attach_alternative(html_content, "text/html")

    if pdf_file:
        msg.attach(filename, pdf_file.getvalue(), "application/pdf")

    msg.send()


def send_receipt_email(to_email, context, pdf_file, filename="receipt.pdf"):
    """
    Spawn a background thread to send the email
    so API response isn't blocked by SMTP latency.
    """
    thread = threading.Thread(
        target=_send_mail, args=(to_email, context, pdf_file, filename), daemon=True
    )
    thread.start()
