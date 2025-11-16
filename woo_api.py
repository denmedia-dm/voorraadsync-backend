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
import requests
import json

with open("config.json") as f:
    CONFIG = json.load(f)

WC_URL = CONFIG["woocommerce"]["url"]
WC_KEY = CONFIG["woocommerce"]["consumer_key"]
WC_SECRET = CONFIG["woocommerce"]["consumer_secret"]

def get_woo_products():
    """
    WooCommerce tüm ürünleri (sayfa sayfa) çeker.
    """
    all_products = []
    page = 1
    per_page = 100  # en yüksek limit

    while True:
        url = f"{WC_URL}/wp-json/wc/v3/products?page={page}&per_page={per_page}"
        response = requests.get(url, auth=(WC_KEY, WC_SECRET))

        products = response.json()

        if not products:
            break  # ürün bitti

        all_products.extend(products)

        # sayfa bilgisi bitti mi kontrol
        if "X-WP-TotalPages" in response.headers:
            total_pages = int(response.headers["X-WP-TotalPages"])
            if page >= total_pages:
                break

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
