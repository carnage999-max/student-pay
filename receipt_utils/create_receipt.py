# receipt_utils/create_receipt.py
from django.conf import settings
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
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

# Register font once
pdfmetrics.registerFont(TTFont("DejaVuSans", FONT_PATH))

# Use A4 page to give more room to long names
PAGE_SIZE = A4
PAGE_WIDTH, PAGE_HEIGHT = PAGE_SIZE

# sensible content margins
LEFT_MARGIN = 40
RIGHT_MARGIN = PAGE_WIDTH - 40
TOP_MARGIN = PAGE_HEIGHT - 40
BOTTOM_MARGIN = 30


def load_image(source) -> ImageReader | None:
    """
    Load image from URL or local file into ImageReader.
    NOTE: network fetches here can be slow — prefer caching images at upload time.
    """
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
        # swallow errors; receipt still renders without that image
        print(f"Error loading image: {e}")
    return None


def _get_verify_url(receipt_hash: str) -> str:
    base = getattr(settings, "SITE_URL", None) or "http://localhost:8000"
    return f"{base.rstrip('/')}/payment/pay/verify-receipt/?hash={receipt_hash}"


def _wrap_text_to_lines(canvas_obj, text, font_name, font_size, max_width):
    """
    Break text into lines that fit within max_width using canvas.stringWidth.
    Returns list of lines.
    """
    if not text:
        return []
    words = text.strip().split()
    lines = []
    cur = []
    for w in words:
        test = " ".join(cur + [w]) if cur else w
        if canvas_obj.stringWidth(test, font_name, font_size) <= max_width:
            cur.append(w)
        else:
            if cur:
                lines.append(" ".join(cur))
            cur = [w]
    if cur:
        lines.append(" ".join(cur))
    return lines


def generate_receipt(data: dict) -> io.BytesIO:
    """
    Generate a receipt PDF on A4 that handles long department names safely.
    Expects data dict with keys:
      - header (str)
      - department_name (str)
      - department_logo (URL or local path) [optional]
      - date, received_from, payment_for, amount_words, amount
      - president_signature, financial_signature (URLs or paths) [optional]
      - receipt_hash (str)
    """
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=PAGE_SIZE)
    width, height = PAGE_WIDTH, PAGE_HEIGHT

    # Pre-calc logo slots
    logo_w, logo_h = 72, 72  # bigger logos on A4 (points)
    logo_top_y = TOP_MARGIN - logo_h + 10

    # Load logos (school logo is local default)
    school_logo = load_image(SCHOOL_LOGO_PATH)
    dept_logo = load_image(data.get("department_logo"))

    # Draw logos
    if school_logo:
        c.drawImage(
            school_logo,
            LEFT_MARGIN,
            logo_top_y,
            width=logo_w,
            height=logo_h,
            preserveAspectRatio=True,
            mask="auto",
        )
    if dept_logo:
        c.drawImage(
            dept_logo,
            RIGHT_MARGIN - logo_w,
            logo_top_y,
            width=logo_w,
            height=logo_h,
            preserveAspectRatio=True,
            mask="auto",
        )

    # === HEADER (bounded between logos) ===
    gap_left = LEFT_MARGIN + logo_w + 16
    gap_right = RIGHT_MARGIN - logo_w - 16
    header_max_width = gap_right - gap_left
    header_center_x = (gap_left + gap_right) / 2

    # choose base font size and shrink if needed for longest word
    base_font_size = 18
    longest_word = max(
        (w for w in (data.get("header", "") or "").split()), key=len, default=""
    )
    font_size = base_font_size
    while (
        font_size > 8
        and c.stringWidth(longest_word, "Helvetica-Bold", font_size) > header_max_width
    ):
        font_size -= 1

    # wrap header into lines
    header_text = data.get("header", "") or ""
    header_lines = _wrap_text_to_lines(
        c, header_text, "Helvetica-Bold", font_size, header_max_width
    )

    # compute header block height and starting y
    line_height = font_size + 4
    header_block_height = len(header_lines) * line_height
    header_start_y = TOP_MARGIN - 8  # a little below top
    # draw header lines centered within header box
    c.setFont("Helvetica-Bold", font_size)
    y = header_start_y
    for line in header_lines:
        c.drawCentredString(header_center_x, y, line)
        y -= line_height

    # Receipt tag on right of header area
    c.setFont("Helvetica-Bold", 11)
    c.rect(header_center_x + header_max_width / 2 - 60, header_start_y - 4, 70, 18)
    c.drawCentredString(
        header_center_x + header_max_width / 2 - 25, header_start_y, "RECEIPT"
    )

    # After header block, start body below it with padding
    body_start_y = header_start_y - header_block_height - 18
    if body_start_y < (height / 2):
        # Ensure we have enough space; if header consumed too much, push further down
        body_start_y = header_start_y - header_block_height - 18

    # === BODY (left column) ===
    c.setFont("Helvetica", 11)
    line_y = body_start_y
    spacing = 20

    def draw_label_line(label, value):
        nonlocal line_y
        if value is None:
            value = ""
        label_txt = f"{label} "
        c.setFont("Helvetica-Bold", 10)
        c.drawString(LEFT_MARGIN, line_y, label_txt)
        label_w = c.stringWidth(label_txt, "Helvetica-Bold", 10)
        c.setFont("Helvetica", 10)
        # wrap value into multiple lines if too wide
        avail_width = width - LEFT_MARGIN - 120  # leave space for things on right
        wrapped = _wrap_text_to_lines(c, str(value), "Helvetica", 10, avail_width)
        if wrapped:
            # draw first line next to label
            c.drawString(LEFT_MARGIN + label_w + 6, line_y, wrapped[0])
            line_y -= spacing
            for cont in wrapped[1:]:
                c.drawString(LEFT_MARGIN + label_w + 6, line_y, cont)
                line_y -= spacing
        else:
            c.drawString(LEFT_MARGIN + label_w + 6, line_y, "")
            line_y -= spacing

    draw_label_line("Date:", data.get("date", ""))
    draw_label_line("Received from:", data.get("received_from", ""))
    draw_label_line("Being the Payment of:", data.get("payment_for", ""))
    draw_label_line("The sum of:", data.get("amount_words", ""))

    # leave some space before signatures/amount
    line_y -= 6

    # === SIGNATURES area (bottom) and AMOUNT box centered horizontally) ===
    sig_y = 110  # consistent bottom area above footer
    sig_h = 40
    # President signature (left)
    pres_sig = load_image(data.get("president_signature"))
    if pres_sig:
        c.drawImage(
            pres_sig,
            LEFT_MARGIN,
            sig_y,
            width=120,
            height=sig_h,
            preserveAspectRatio=True,
            mask="auto",
        )
    c.line(LEFT_MARGIN, sig_y - 6, LEFT_MARGIN + 140, sig_y - 6)
    c.setFont("Helvetica", 9)
    c.drawString(LEFT_MARGIN, sig_y - 20, "President")

    # Financial signature (right)
    fin_sig = load_image(data.get("financial_signature"))
    if fin_sig:
        fin_sig_x = RIGHT_MARGIN - 140
        c.drawImage(
            fin_sig,
            fin_sig_x,
            sig_y,
            width=120,
            height=sig_h,
            preserveAspectRatio=True,
            mask="auto",
        )
    c.line(RIGHT_MARGIN - 140, sig_y - 6, RIGHT_MARGIN, sig_y - 6)
    c.drawRightString(RIGHT_MARGIN, sig_y - 20, "Financial Secretary")

    # Amount box centered above signatures
    amount_box_w, amount_box_h = 160, 28
    amount_box_x = (width - amount_box_w) / 2
    amount_box_y = sig_y + sig_h + 10
    c.rect(amount_box_x, amount_box_y, amount_box_w, amount_box_h)
    c.setFont("DejaVuSans", 12)
    c.drawCentredString(
        amount_box_x + amount_box_w / 2,
        amount_box_y + amount_box_h / 2 - 4,
        f"₦ {data.get('amount', '')}",
    )

    # === SECURITY HASH + QR ===
    receipt_hash = data.get("receipt_hash", "")
    c.setFont("Helvetica", 8)
    c.drawString(LEFT_MARGIN, BOTTOM_MARGIN, f"Verify: {receipt_hash}")

    verify_url = _get_verify_url(receipt_hash)
    qr = qrcode.QRCode(box_size=4, border=1)
    qr.add_data(verify_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    qr_io = io.BytesIO()
    qr_img.save(qr_io, format="PNG")
    qr_io.seek(0)
    qr_reader = ImageReader(qr_io)

    # Place QR to the right of the amount box but above signatures
    qr_size = 120
    qr_x = amount_box_x + amount_box_w + 12
    if qr_x + qr_size > RIGHT_MARGIN:
        qr_x = amount_box_x - qr_size - 12
    qr_y = amount_box_y + (amount_box_h - qr_size) / 2
    c.drawImage(
        qr_reader,
        qr_x,
        qr_y,
        width=qr_size,
        height=qr_size,
        preserveAspectRatio=True,
        mask="auto",
    )

    # === WATERMARK (drawn last, auto-scale) ===
    watermark_text = (data.get("department_name") or data.get("header") or "").strip()
    if watermark_text:
        # choose a base watermark size relative to page width, then reduce if the text is very long
        base_size = 80
        wm_font = "Helvetica-Bold"
        wm_size = base_size

        # compute a rough width for the watermark text and scale down if necessary
        text_width = c.stringWidth(watermark_text, wm_font, wm_size)
        max_wm_width = width * 0.9
        if text_width > max_wm_width:
            wm_size = max(int(wm_size * max_wm_width / text_width), 24)

        c.saveState()
        # try transparency; fallback to light gray
        try:
            c.setFillAlpha(0.12)
            c.setFillColorRGB(0.05, 0.05, 0.05)
        except Exception:
            c.setFillGray(0.88)
        c.setFont(wm_font, wm_size)
        c.translate(width / 2, height / 2)
        c.rotate(30)
        # Ensure very long names are split into two lines for watermark readability
        wm_lines = _wrap_text_to_lines(
            c, watermark_text, wm_font, wm_size, max_wm_width
        )
        line_h = wm_size + 6
        start_y = (len(wm_lines) - 1) * (line_h / 2)
        for i, ln in enumerate(wm_lines):
            c.drawCentredString(0, start_y - i * line_h, ln.upper())
        c.restoreState()

    # finish
    c.showPage()
    c.save()
    buf.seek(0)
    return buf
