import requests
import json
import base64
import time

with open("config.json") as f:
    CONFIG = json.load(f)

CLIENT_ID = CONFIG["bol"]["client_id"]
CLIENT_SECRET = CONFIG["bol"]["client_secret"]

# Token cache
access_token = None
token_expiry = 0

def get_access_token():
    global access_token, token_expiry

    # Token geçerli ise yeniden alma
    if access_token and time.time() < token_expiry:
        return access_token

    # Client ID + Secret -> Base64 encode
    auth = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()

    url = "https://api.bol.com/retailer/oauth/token"
    headers = {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type": "client_credentials"}

    response = requests.post(url, headers=headers, data=data)

    if response.status_code != 200:
        return {"error": response.text, "status": response.status_code}

    token_json = response.json()
    access_token = token_json["access_token"]
    token_expiry = time.time() + token_json["expires_in"] - 30  # token + margin

    return access_token


def get_bol_products():
    token = get_access_token()

    if isinstance(token, dict):  # hata
        return token

    url = "https://api.bol.com/retailer/products"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.retailer.v10+json"
    }

    response = requests.get(url, headers=headers)

    try:
        return response.json()
    except:
        return {"error": response.text, "status": response.status_code}
