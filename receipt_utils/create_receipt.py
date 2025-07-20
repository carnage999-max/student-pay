from reportlab.pdfgen import canvas
from datetime import datetime
from reportlab.lib.units import inch
import os, io

# For proper Unicode support (for example, to render the ₦ sign)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))

# Receipt size in points (1 inch = 72 points)
RECEIPT_WIDTH = 6.75 * inch  # 486 pt
RECEIPT_HEIGHT = 3.375 * inch  # 243 pt
RECEIPT_SIZE = (RECEIPT_WIDTH, RECEIPT_HEIGHT)

def generate_receipt(data: dict) -> io.BytesIO:
    buffer = io.BytesIO()
    
    c = canvas.Canvas(buffer, pagesize=RECEIPT_SIZE)
    width, height = RECEIPT_SIZE

    # Margins
    left_margin = 30
    right_margin = width - 30

    # === LOGO (Left & Right) ===
    logo_path = data.get("logo_path")
    if logo_path and os.path.exists(logo_path):
        logo_width = 35
        logo_height = 35
        # Left logo
        c.drawImage(logo_path, left_margin, height - 45, width=logo_width, height=logo_height, preserveAspectRatio=True)
        # Right logo
        c.drawImage(logo_path, right_margin - logo_width, height - 45, width=logo_width, height=logo_height, preserveAspectRatio=True)

    # === HEADER ===
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width / 2, height - 30, data['header'])

    # RECEIPT Box in header
    c.setFont("Helvetica-Bold", 11)
    c.rect(width / 2 - 35, height - 50, 70, 18)
    c.drawCentredString(width / 2, height - 46, "RECEIPT")

    # === BODY (label + line layout) ===
    c.setFont("Helvetica", 10)
    line_y = height - 75
    spacing = 17

    def draw_label_line(label, value, x, y, double_line=False):
        label_text = f"{label} "
        c.drawString(x, y, label_text)
        label_width = c.stringWidth(label_text, "Helvetica", 10)
        line_start_x = x + label_width + 5
        c.drawString(line_start_x, y, value)

        line_end_x = width - 40
        c.line(line_start_x, y - 2, line_end_x, y - 2)

        if double_line:
            c.line(line_start_x, y - 2 - spacing, line_end_x, y - 2 - spacing)

    draw_label_line("Date:", data['date'], left_margin, line_y)
    line_y -= spacing

    draw_label_line("Received from:", data['received_from'], left_margin, line_y)
    line_y -= spacing

    draw_label_line("Being the Payment of:", data['payment_for'], left_margin, line_y)
    line_y -= spacing

    draw_label_line("The sum of:", data['amount_words'], left_margin, line_y, double_line=True)
    line_y -= spacing * 1.5

    # === SIGNATURES AND AMOUNT BOX ===
    signature_y = 40
    signature_height = 25
    signature_width = 60

    # President Signature Image
    pres_sig_path = data.get("president_signature")
    if pres_sig_path and os.path.exists(pres_sig_path):
        c.drawImage(pres_sig_path, left_margin, signature_y, width=signature_width, height=signature_height, preserveAspectRatio=True)
    c.line(left_margin, signature_y, left_margin + 80, signature_y)
    c.drawString(left_margin, signature_y - 12, "President")

    # Financial Secretary Signature Image
    fin_sig_path = data.get("financial_signature")
    if fin_sig_path and os.path.exists(fin_sig_path):
        c.drawImage(fin_sig_path, right_margin - signature_width, signature_y, width=signature_width, height=signature_height, preserveAspectRatio=True)
    c.line(right_margin - 80, signature_y, right_margin, signature_y)
    c.drawRightString(right_margin, signature_y - 12, "Financial Secretary")

    # Amount Box
    amount_box_width = 80
    amount_box_height = 20
    amount_box_x = (width - amount_box_width) / 2
    amount_box_y = signature_y - (amount_box_height / 2)

    c.rect(amount_box_x, amount_box_y, amount_box_width, amount_box_height)
    c.setFont("DejaVuSans", 11)
    c.drawCentredString(amount_box_x + amount_box_width / 2, amount_box_y + 6, f"₦ {data['amount']}")

    c.showPage()
    c.save()
    
    buffer.seek(0)
    return buffer

# === Example Usage ===
if __name__ == "__main__":
    data = {
        "header": "XYZ ASSOCIATION",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "received_from": "John Doe",
        "payment_for": "Annual Dues",
        "amount_words": "Five Thousand Naira Only",
        "amount": "5000",
        "logo_path": "logo.png",
        "president_signature": "president_sig.png",
        "financial_signature": "finsec_sig.png"
    }

    generate_receipt(data)
