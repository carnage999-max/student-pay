from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os, io, requests

pdfmetrics.registerFont(TTFont("DejaVuSans", "DejaVuSans.ttf"))

# Receipt size in points (1 inch = 72 points)
RECEIPT_WIDTH = 6.75 * inch  # 486 pt
RECEIPT_HEIGHT = 3.375 * inch  # 243 pt
RECEIPT_SIZE = (RECEIPT_WIDTH, RECEIPT_HEIGHT)

# === Static path to school logo ===
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCHOOL_LOGO_PATH = os.path.join(
    SCRIPT_DIR, "school_logo.png"
)  # ← ensure this file exists


def load_image(source) -> ImageReader | None:
    """
    This function loads an image from a given source, either a URL or a local file path, and returns an
    ImageReader object if successful.

    :param source: The `load_image` function takes a `source` parameter, which should be a string
    representing the location of an image file. The function attempts to load the image from the
    specified source, whether it is a URL (starting with "http://" or "https://") or a local file path
    :return: The function `load_image` returns an `ImageReader` object if the image is successfully
    loaded from the specified source (either a URL or a local file path). If there is an error during
    the loading process, it returns `None`.
    """
    if not isinstance(source, str) or not source.strip():
        return None
    try:
        if source.startswith("http://") or source.startswith("https://"):
            response = requests.get(source, timeout=5)
            if response.status_code == 200:
                return ImageReader(io.BytesIO(response.content))
        elif os.path.exists(source):
            return ImageReader(source)
    except Exception as e:
        print(f"Error loading image: {e}")
    return None


def generate_receipt(data: dict) -> io.BytesIO:
    """
    The function `generate_receipt` creates a PDF receipt with logos, header, body information,
    signatures, and an amount box.

    :param data: The `data` parameter in the `generate_receipt` function is a dictionary containing
    information needed to generate a receipt. The dictionary should have the following keys:
    :type data: dict
    :return: The function `generate_receipt` returns an `io.BytesIO` object containing the generated
    receipt in PDF format.
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=RECEIPT_SIZE)
    width, height = RECEIPT_SIZE

    # Margins
    left_margin = 30
    right_margin = width - 30

    # === LOGOS ===
    logo_width = 40
    logo_height = 40
    logo_y = height - logo_height - 5

    # Draw school logo (left)
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

    # Draw department logo (right)
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
    c.drawCentredString(width / 2, height - 30, data["header"])

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
        c.drawString(line_start_x, y, value)
        line_end_x = width - 40
        c.line(line_start_x, y - 2, line_end_x, y - 2)
        if double_line:
            c.line(line_start_x, y - 2 - spacing, line_end_x, y - 2 - spacing)

    draw_label_line("Date:", data["date"], left_margin, line_y)
    line_y -= spacing

    draw_label_line("Received from:", data["received_from"], left_margin, line_y)
    line_y -= spacing

    draw_label_line("Being the Payment of:", data["payment_for"], left_margin, line_y)
    line_y -= spacing

    draw_label_line(
        "The sum of:", data["amount_words"], left_margin, line_y, double_line=True
    )
    line_y -= spacing * 1.5

    # === SIGNATURES ===
    signature_y = 40
    signature_height = 25
    signature_width = 60

    # President Signature
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

    # Financial Secretary Signature
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
        amount_box_x + amount_box_width / 2, amount_box_y + 6, f"₦ {data['amount']}"
    )

    c.showPage()
    c.save()

    buffer.seek(0)
    return buffer
