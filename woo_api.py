import requests
import json

with open("config.json") as f:
    CONFIG = json.load(f)

WC_URL = CONFIG["woocommerce"]["url"]
WC_KEY = CONFIG["woocommerce"]["consumer_key"]
WC_SECRET = CONFIG["woocommerce"]["consumer_secret"]


def get_woo_products():
    """
    WooCommerce'teki sadece gerçek – yayınlanmış – stok yönetimi olan ürünleri çeker.
    'Concept', 'Draft', 'Private', 'Parent Product' ürünleri hariç tutar.
    """
    
    all_products = []
    page = 1
    per_page = 100  # WooCommerce'in izin verdiği maksimum değer

    while True:
        params = {
            "page": page,
            "per_page": per_page,
            "status": "publish"        # sadece canlı ürünler
        }

        url = f"{WC_URL}/wp-json/wc/v3/products"
        response = requests.get(url, auth=(WC_KEY, WC_SECRET), params=params)

        products = response.json()

        # ürün yoksa döngüyü kır
        if not products or len(products) == 0:
            break

        for p in products:

            # 1) Parent product olanları çıkar
            if p.get("type") == "variable":
                continue

            # 2) stock yönetimi olmayanları çıkar
            if not p.get("manage_stock", False):
                continue

            # 3) Concept / taslak / private zaten gelmez — publish filter var
            # ama yine de güvenlik olsun diye:
            if p.get("status") != "publish":
                continue

            # 4) Varyasyon ve simple ürünleri dahil et
            if p.get("type") in ["simple", "variation"]:
                all_products.append(p)

        page += 1

    return all_products



def update_stock(product_id, quantity):
    """
    WooCommerce stok güncelleme
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

    try:
        return response.json()
    except:
        return {"error": response.text}
