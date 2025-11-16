import requests
import json

with open("config.json") as f:
    CONFIG = json.load(f)

WC_URL = CONFIG["woocommerce"]["url"]
WC_KEY = CONFIG["woocommerce"]["consumer_key"]
WC_SECRET = CONFIG["woocommerce"]["consumer_secret"]


# ---------------------------------------------------------
# 🚀 OPTİMİZE EDİLMİŞ ÜRÜN ÇEKME (SAYFALI)
# ---------------------------------------------------------
def get_woo_products(page=1, per_page=50):
    """
    WooCommerce ürünlerini SAYFA SAYFA çeker.
    Performanslı ve Render için güvenlidir.
    """

    params = {
        "page": page,
        "per_page": per_page,
        "status": "publish",      # sadece canlı ürünler
        "orderby": "id",
        "order": "asc"
    }

    url = f"{WC_URL}/wp-json/wc/v3/products"
    response = requests.get(url, auth=(WC_KEY, WC_SECRET), params=params)

    if response.status_code != 200:
        return {"error": "WooCommerce API error", "detail": response.text}

    products = response.json()

    # Filtreleme: sadece gerçek stok yönetimli ürünler
    filtered = []

    for p in products:

        # Parent variable product → atla
        if p.get("type") == "variable":
            continue

        # Stok yönetimi yoksa → atla
        if not p.get("manage_stock", False):
            continue

        # Güvenlik: publish olmayan gelmez ama kontrol edelim
        if p.get("status") != "publish":
            continue

        # Simple veya Variation ürünleri al
        if p.get("type") in ["simple", "variation"]:
            filtered.append(p)

    # WooCommerce toplam sayfa bilgisini header'dan alıyoruz
    total_pages = int(response.headers.get("X-WP-TotalPages", 1))
    total_items = int(response.headers.get("X-WP-Total", len(filtered)))

    return {
        "items": filtered,
        "total_pages": total_pages,
        "total_items": total_items,
        "page": page,
        "per_page": per_page
    }


# ---------------------------------------------------------
# 🟦 WooCommerce stok güncelleme
# ---------------------------------------------------------
def update_stock(product_id, quantity):
    """
    WooCommerce stok güncelleme endpointi
    """
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

    if response.status_code not in (200, 201):
        return {"error": response.text}

    return response.json()
