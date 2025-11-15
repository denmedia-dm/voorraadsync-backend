import requests
import json
import base64
import time

# Load config
with open("config.json") as f:
    CONFIG = json.load(f)

CLIENT_ID = CONFIG["bol"]["client_id"]
CLIENT_SECRET = CONFIG["bol"]["client_secret"]

# Cache
access_token = None
token_expiry = 0


def get_access_token():
    """
    Haalt een OAuth access token op bij Bol.com
    """
    global access_token, token_expiry

    # Token hala geçerliyse tekrar alma
    if access_token and time.time() < token_expiry:
        return access_token

    # Client ID + Secret → Base64
    auth_string = f"{CLIENT_ID}:{CLIENT_SECRET}"
    auth_encoded = base64.b64encode(auth_string.encode()).decode()

    url = "https://api.bol.com/retailer/oauth/token"
    headers = {
        "Authorization": f"Basic {auth_encoded}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type": "client_credentials"}

    response = requests.post(url, headers=headers, data=data)

    # Token alınamadıysa detaylı hata göster
    if response.status_code != 200:
        return {
            "error": "token_error",
            "status": response.status_code,
            "body": response.text
        }

    json_data = response.json()
    access_token = json_data["access_token"]
    token_expiry = time.time() + json_data["expires_in"] - 30

    return access_token


def get_bol_products():
    """
    Haalt producten op uit Bol API
    """
    token = get_access_token()

    # Eğer token dict ise hata var demektir
    if isinstance(token, dict):
        return token

    url = "https://api.bol.com/retailer/products"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.retailer.v10+json"
    }

    response = requests.get(url, headers=headers)

    # Boş response ise
    if not response.text:
        return {"error": "empty response", "status": response.status_code}

    # JSON parse etmeyi dene
    try:
        return response.json()
    except:
        return {
            "error": "json_parse_error",
            "status": response.status_code,
            "body": response.text
        }
