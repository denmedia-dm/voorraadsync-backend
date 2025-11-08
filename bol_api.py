import requests
import json
from dotenv import load_dotenv
import os

load_dotenv()

with open("config.json") as f:
    CONFIG = json.load(f)

BOL_CLIENT_ID = CONFIG["bol"]["client_id"]
BOL_CLIENT_SECRET = CONFIG["bol"]["client_secret"]

# Bu endpoint test içindir (ürün listesi gibi örnek fonksiyonlar eklenebilir)
def get_bol_products():
    """
    Haalt een lijst van producten op uit Bol.com API (voorbeeldfunctie)
    Türkçe: Bol.com üzerindeki ürün listesini getirir (örnek)
    """
    url = "https://api.bol.com/retailer-demo/products"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        return {"error": response.text}
