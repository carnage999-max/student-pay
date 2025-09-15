from django.conf import settings
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
from pathlib import Path
import io
import requests
import qrcode


BASE_DIR = Path(__file__).resolve().parent
FONT_PATH = os.path.join(BASE_DIR, "DejaVuSans.ttf")
SCHOOL_LOGO_PATH = os.path.join(BASE_DIR, "school_logo.png")

if not os.path.exists(FONT_PATH):
    raise FileNotFoundError(f"Font file not found at: {FONT_PATH}")
if not os.path.exists(SCHOOL_LOGO_PATH):
    raise FileNotFoundError(f"School logo file not found at: {SCHOOL_LOGO_PATH}")

pdfmetrics.registerFont(TTFont("DejaVuSans", FONT_PATH))

# Receipt size
RECEIPT_WIDTH = 6.75 * inch
RECEIPT_HEIGHT = 3.375 * inch
RECEIPT_SIZE = (RECEIPT_WIDTH, RECEIPT_HEIGHT)


def load_image(source) -> ImageReader | None:
    """Load image from URL or local file into ImageReader."""
    if not isinstance(source, str) or not source.strip():
        return None
    try:
        if source.startswith(("http://", "https://")):
            response = requests.get(source, timeout=5)
            if response.status_code == 200:
                return ImageReader(io.BytesIO(response.content))
        elif os.path.exists(source):
            return ImageReader(source)
    except Exception as e:
        print(f"Error loading image: {e}")
    return None


def draw_multiline_header(
    canvas, text, center_x, start_y, max_width, base_font_size=14
):
    """Break long headers into multiple lines, auto-resize font if too long."""
    font_size = base_font_size
    # shrink font until the longest word fits in max_width
    longest_word = max(text.split(), key=len, default="")
    while (
        canvas.stringWidth(longest_word, "Helvetica-Bold", font_size) > max_width
        and font_size > 8
    ):
        font_size -= 1

    canvas.setFont("Helvetica-Bold", font_size)
    words = text.split()
    lines, current_line = [], []

    for word in words:
        test_line = " ".join(current_line + [word])
        if canvas.stringWidth(test_line, "Helvetica-Bold", font_size) <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))

    # Draw each line centered
    line_height = font_size + 2
    y_pos = start_y
    for line in lines:
        canvas.drawCentredString(center_x, y_pos, line)
        y_pos -= line_height


def _get_verify_url(receipt_hash: str) -> str:
    base = getattr(settings, "SITE_URL", None) or ("http://localhost:8000")
    return f"{base.rstrip('/')}/payment/pay/verify-receipt/?hash={receipt_hash}"


def generate_receipt(data: dict) -> io.BytesIO:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=RECEIPT_SIZE)
    width, height = RECEIPT_SIZE

    left_margin = 30
    right_margin = width - 30

    # === LOGOS ===
    logo_width, logo_height = 40, 40
    logo_y = height - logo_height - 5

    school_logo = load_image(SCHOOL_LOGO_PATH)
    if school_logo:
        c.drawImage(
            school_logo,
            left_margin,
            logo_y,
            width=logo_width,
            height=logo_height,
            preserveAspectRatio=True,
        )

    dept_logo = load_image(data.get("department_logo"))
    if dept_logo:
        c.drawImage(
            dept_logo,
            right_margin - logo_width,
            logo_y,
            width=logo_width,
            height=logo_height,
            preserveAspectRatio=True,
        )

    # === HEADER (bounded between logos, dynamically scaled) ===
    max_header_x_left = left_margin + logo_width + 15
    max_header_x_right = right_margin - logo_width - 15
    max_header_width = max_header_x_right - max_header_x_left
    center_x = (max_header_x_left + max_header_x_right) / 2

    draw_multiline_header(
        c,
        data.get("header", ""),
        center_x,
        height - 30,
        max_header_width,
    )

    # Receipt tag
    c.setFont("Helvetica-Bold", 11)
    c.rect(width / 2 - 35, height - 50, 70, 18)
    c.drawCentredString(width / 2, height - 80, "RECEIPT")

    # === BODY ===
    c.setFont("Helvetica", 10)
    line_y, spacing = height - 75, 17

    def draw_label_line(label, value, x, y, double_line=False):
        label_text = f"{label} "
        c.drawString(x, y, label_text)
        label_width = c.stringWidth(label_text, "Helvetica", 10)
        line_start_x = x + label_width + 5
        c.drawString(line_start_x, y, str(value))
        line_end_x = width - 40
        c.line(line_start_x, y - 2, line_end_x, y - 2)
        if double_line:
            c.line(line_start_x, y - 2 - spacing, line_end_x, y - 2 - spacing)

    draw_label_line("Date:", data.get("date", ""), left_margin, line_y)
    line_y -= spacing
    draw_label_line(
        "Received from:", data.get("received_from", ""), left_margin, line_y
    )
    line_y -= spacing
    draw_label_line(
        "Being the Payment of:", data.get("payment_for", ""), left_margin, line_y
    )
    line_y -= spacing
    draw_label_line(
        "The sum of:",
        data.get("amount_words", ""),
        left_margin,
        line_y,
        double_line=True,
    )
    line_y -= spacing * 1.5

    # === SIGNATURES ===
    signature_y, signature_height, signature_width = 40, 25, 60
    pres_sig = load_image(data.get("president_signature"))
    if pres_sig:
        c.drawImage(
            pres_sig,
            left_margin,
            signature_y,
            width=signature_width,
            height=signature_height,
            preserveAspectRatio=True,
        )
    c.line(left_margin, signature_y, left_margin + 80, signature_y)
    c.drawString(left_margin, signature_y - 12, "President")

    fin_sig = load_image(data.get("financial_signature"))
    if fin_sig:
        c.drawImage(
            fin_sig,
            right_margin - signature_width,
            signature_y,
            width=signature_width,
            height=signature_height,
            preserveAspectRatio=True,
        )
    c.line(right_margin - 80, signature_y, right_margin, signature_y)
    c.drawRightString(right_margin, signature_y - 12, "Financial Secretary")

    # === AMOUNT BOX ===
    amount_box_width, amount_box_height = 80, 20
    amount_box_x = (width - amount_box_width) / 2
    amount_box_y = signature_y - (amount_box_height / 2)

    c.rect(amount_box_x, amount_box_y, amount_box_width, amount_box_height)
    c.setFont("DejaVuSans", 11)
    c.drawCentredString(
        amount_box_x + amount_box_width / 2,
        amount_box_y + 6,
        f"₦ {data.get('amount', '')}",
    )

    # === SECURITY HASH + QR ===
    receipt_hash = data.get("receipt_hash", "")
    c.setFont("Helvetica", 7)
    c.drawString(left_margin, 15, f"Verify: {receipt_hash}")

    verify_url = _get_verify_url(receipt_hash)
    qr = qrcode.QRCode(box_size=2, border=1)
    qr.add_data(verify_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")

    qr_io = io.BytesIO()
    qr_img.save(qr_io, format="PNG")
    qr_io.seek(0)
    qr_reader = ImageReader(qr_io)

    qr_size = 40
    qr_x = amount_box_x + amount_box_width + 8
    if qr_x + qr_size > right_margin:
        qr_x = amount_box_x - qr_size - 8
    qr_y = amount_box_y - 5
    c.drawImage(qr_reader, qr_x, qr_y, width=qr_size, height=qr_size)

    # === WATERMARK ===
    dept_for_watermark = data.get("department_name") or data.get("header") or ""
    if dept_for_watermark:
        c.saveState()
        c.setFont("Helvetica-Bold", 36)
        try:
            c.setFillAlpha(0.12)
            c.setFillColorRGB(0.1, 0.1, 0.1)
        except Exception:
            c.setFillGray(0.85)
        c.translate(width / 2, height / 2)
        c.rotate(30)
        c.drawCentredString(0, 0, str(dept_for_watermark).upper())
        c.restoreState()

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer
