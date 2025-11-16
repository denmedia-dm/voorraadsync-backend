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
    """
    WooCommerce'teki sadece yayınlanmış gerçek ürünleri listeler
    """
    url = f"{WC_URL}/wp-json/wc/v3/products"
    params = {
        "status": "publish",       # sadece canlı ürünler
        "per_page": 100,           # WooCommerce max 100 destekliyor
    }

    all_products = []
    page = 1

    while True:
        params["page"] = page
        response = requests.get(url, auth=(WC_KEY, WC_SECRET), params=params)
        products = response.json()

        if not products or len(products) == 0:
            break

        # Concept / parent / stok olmayan ürünleri temizleyelim
        for p in products:
            if p.get("type") in ["simple", "variation"] and p.get("status") == "publish":
                all_products.append(p)

        page += 1

    return all_products


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
