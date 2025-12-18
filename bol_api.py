import requests
import json
import time

with open("config.json") as f:
    CONFIG = json.load(f)

BOL_CLIENT_ID = CONFIG["bol"]["client_id"]
BOL_CLIENT_SECRET = CONFIG["bol"]["client_secret"]

TOKEN_URL = "https://login.bol.com/token"

# Bellekte token tutacağız (şimdilik)
_access_token = None
_token_expires_at = 0

def get_access_token():
    """
    Bol.com access token alır.
    Süresi dolmuşsa otomatik yeniler.
    """
    global _access_token, _token_expires_at

    # Token hâlâ geçerliyse direkt dön
    if _access_token and time.time() < _token_expires_at:
        return _access_token

    payload = {
        "grant_type": "client_credentials"
    }

    response = requests.post(
        TOKEN_URL,
        auth=(BOL_CLIENT_ID, BOL_CLIENT_SECRET),
        data=payload
    )

    if response.status_code != 200:
        raise Exception(f"Bol token alınamadı: {response.text}")

    data = response.json()

    _access_token = data["access_token"]
    expires_in = data.get("expires_in", 300)
    _token_expires_at = time.time() + expires_in - 30  # güvenli pay

    return _access_token