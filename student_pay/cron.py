import logging
import os
import requests

logger = logging.getLogger(__name__)


def keep_alive():
    try:
        resp = requests.get("https://student-pay-backend.onrender.com/ping/", headers={"X-Cron-Token": os.getenv("CRON_SECRET_TOKEN")})
        logger.info(f"Keep-alive ping status: {resp.status_code}")
    except Exception as e:
        logger.error(f"Keep-alive failed: {e}")
