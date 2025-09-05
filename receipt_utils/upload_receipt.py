from utils.supabase_util import supabase
from decouple import config
import logging
import requests


logger = logging.getLogger(__name__)


def upload_receipt(filename, pdf_stream):
    """
    The `upload_receipt` function uploads a PDF receipt file to Supabase storage and returns the public
    URL of the uploaded file.

    :param filename: The `filename` parameter in the `upload_receipt` function is a string that
    represents the name of the file being uploaded. It is used to specify the name under which the file
    will be stored in the Supabase storage
    :param pdf_stream: The `pdf_stream` parameter in the `upload_receipt` function is expected to be a
    file stream object containing the PDF data that you want to upload. This stream object should allow
    reading the binary data of the PDF file. You can pass an open file stream object in binary read mode
    as the `
    :return: The `upload_receipt` function returns either the URL of the uploaded receipt if successful,
    or a dictionary with error details if the receipt URL is not found.
    """
    try:
        headers = {
            "apikey": config("SUPABASE_KEY"),
            "Authorization": f"Bearer {config('SUPABASE_KEY')}",
            "Content-Type": "application/pdf",
            "x-upsert": "true",
        }
        url = f"{config('SUPABASE_URL')}/storage/v1/object/receipts/{filename}"

        response = requests.post(url, headers=headers, data=pdf_stream.read())
        response.raise_for_status()

        logging.info(f"Successfully uploaded {filename} to Supabase.")

    except requests.exceptions.RequestException as e:
        if e.response is not None:
            logger.error(f"Response status: {e.response.status_code}")
            logger.error(f"Response text: {e.response.text}")
        raise

    receipt_url = supabase.storage.from_("receipts").get_public_url(filename)
    if receipt_url:
        return receipt_url
    else:
        return {
            "error": "url not found",
            "code": 404,
            "detail": "receipt url not found",
        }
