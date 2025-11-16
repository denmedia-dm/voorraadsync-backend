import requests
import json

# Config yükle
with open("config.json") as f:
    CONFIG = json.load(f)

WC_URL = CONFIG["woocommerce"]["url"]
WC_KEY = CONFIG["woocommerce"]["consumer_key"]
WC_SECRET = CONFIG["woocommerce"]["consumer_secret"]


# -------------------------------------------------------
#   Tüm WooCommerce ürünlerini sınırsız şekilde çek
# -------------------------------------------------------
def get_woo_products():
    products = []
    page = 1

    while True:
        url = f"{WC_URL}/wp-json/wc/v3/products?per_page=100&page={page}"

        response = requests.get(url, auth=(WC_KEY, WC_SECRET))

        try:
            batch = response.json()
        except Exception:
            break

        # Eğer ürün yoksa dur
        if not isinstance(batch, list) or len(batch) == 0:
            break

        products.extend(batch)
        page += 1

    return products


# -------------------------------------------------------
#   WooCommerce stok güncelleme
# -------------------------------------------------------
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
    except Exception:
        return {"error": response.text}
