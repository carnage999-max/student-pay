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

# Register the font
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
            # network fetch (consider caching these at upload time to avoid latency)
            response = requests.get(source, timeout=5)
            if response.status_code == 200:
                return ImageReader(io.BytesIO(response.content))
        elif os.path.exists(source):
            return ImageReader(source)
    except Exception as e:
        # Keep failures quiet — receipt still renders without the image
        print(f"Error loading image: {e}")
    return None


def _get_verify_url(receipt_hash: str) -> str:
    """Build verify URL (use settings.SITE_URL if provided)."""
    base = getattr(settings, "SITE_URL", None) or ("http://localhost:8000")
    return f"{base.rstrip('/')}/pay/verify/?hash={receipt_hash}"


def generate_receipt(data: dict) -> io.BytesIO:
    """
    Creates a PDF receipt with:
      - Logos
      - Header
      - Body info
      - Signatures
      - Amount box
      - Verification hash + QR code (positioned next to amount box)
      - Watermark (department name; drawn last so it sits on top)
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=RECEIPT_SIZE)
    width, height = RECEIPT_SIZE

    left_margin = 30
    right_margin = width - 30

    # === LOGOS ===
    logo_width = 40
    logo_height = 40
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

    # dept logo can be a URL or local path in data["department_logo"]
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

    # === HEADER ===
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width / 2, height - 30, data.get("header", ""))

    # Receipt tag
    c.setFont("Helvetica-Bold", 11)
    c.rect(width / 2 - 35, height - 50, 70, 18)
    c.drawCentredString(width / 2, height - 46, "RECEIPT")

    # === BODY ===
    c.setFont("Helvetica", 10)
    line_y = height - 75
    spacing = 17

    def draw_label_line(label, value, x, y, double_line=False):
        label_text = f"{label} "
        c.drawString(x, y, label_text)
        label_width = c.stringWidth(label_text, "Helvetica", 10)
        line_start_x = x + label_width + 5
        # if value is long, it will wrap visually; keep it simple for now
        c.drawString(line_start_x, y, str(value))
        line_end_x = width - 40
        c.line(line_start_x, y - 2, line_end_x, y - 2)
        if double_line:
            c.line(line_start_x, y - 2 - spacing, line_end_x, y - 2 - spacing)

    # required fields expected in data: date, received_from, payment_for, amount_words, amount
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
    signature_y = 40
    signature_height = 25
    signature_width = 60

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
    amount_box_width = 80
    amount_box_height = 20
    amount_box_x = (width - amount_box_width) / 2
    amount_box_y = signature_y - (amount_box_height / 2)

    c.rect(amount_box_x, amount_box_y, amount_box_width, amount_box_height)
    c.setFont("DejaVuSans", 11)
    c.drawCentredString(
        amount_box_x + amount_box_width / 2,
        amount_box_y + 6,
        f"₦ {data.get('amount', '')}",
    )

    # === SECURITY HASH + QR (placed to the right of amount box, not over signatures) ===
    receipt_hash = data.get("receipt_hash", "")
    c.setFont("Helvetica", 7)
    c.drawString(left_margin, 15, f"Verify: {receipt_hash}")

    # Compose verify URL
    verify_url = _get_verify_url(receipt_hash)

    # Build QR (in-memory)
    qr = qrcode.QRCode(box_size=2, border=1)
    qr.add_data(verify_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")

    qr_io = io.BytesIO()
    qr_img.save(qr_io, format="PNG")
    qr_io.seek(0)
    qr_reader = ImageReader(qr_io)

    # Position QR immediately to the right of the amount box and keep it from overlapping signatures
    qr_size = 40  # px (keeps QR compact)
    qr_x = amount_box_x + amount_box_width + 8
    # If QR would run off the page to the right, move it left of the amount box instead
    if qr_x + qr_size > right_margin:
        qr_x = amount_box_x - qr_size - 8
    qr_y = amount_box_y - 5  # slightly below the amount box center

    c.drawImage(qr_reader, qr_x, qr_y, width=qr_size, height=qr_size)

    # === WATERMARK (drawn last so it appears on top) ===
    dept_for_watermark = data.get("department_name") or data.get("header") or ""
    if dept_for_watermark:
        c.saveState()
        # larger but not overwhelming
        c.setFont("Helvetica-Bold", 36)
        # Try to use alpha if available, otherwise fall back to light gray
        try:
            c.setFillAlpha(0.12)  # if supported by ReportLab version
            c.setFillColorRGB(0.1, 0.1, 0.1)  # dark but transparent
        except Exception:
            # fallback: light gray (no alpha)
            c.setFillGray(0.85)
        # center, rotate and draw
        c.translate(width / 2, height / 2)
        c.rotate(30)
        c.drawCentredString(0, 0, str(dept_for_watermark).upper())
        c.restoreState()

    # Finish
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer
