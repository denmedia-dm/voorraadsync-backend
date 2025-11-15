import requests
import json

with open("config.json") as f:
    CONFIG = json.load(f)

WC_URL = CONFIG["woocommerce"]["url"]
WC_KEY = CONFIG["woocommerce"]["consumer_key"]
WC_SECRET = CONFIG["woocommerce"]["consumer_secret"]

def get_woo_products():
    """
    WooCommerce'deki tüm ürünleri listeler
    """
    url = f"{WC_URL}/wp-json/wc/v3/products"
    response = requests.get(url, auth=(WC_KEY, WC_SECRET))
    return response.json()

def update_woo_stock(product_id, new_stock):
    """
    WooCommerce'te stok günceller
    """
    url = f"{WC_URL}/wp-json/wc/v3/products/{product_id}"
    data = {"stock_quantity": new_stock}
    response = requests.put(url, auth=(WC_KEY, WC_SECRET), json=data)
    return response.json()
def update_stock(product_id, quantity):
    url = f"{WC_URL}/wp-json/wc/v3/products/{product_id}"
    data = {
        "stock_quantity": quantity,
        "manage_stock": True
    }

    response = requests.put(
        url,
        auth=(WC_KEY, WC_SECRET),
        json=data
    )

    try:
        return response.json()
    except:
        return {"error": response.text}
