from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from datetime import datetime

import woo_api
import bol_api

app = FastAPI()

templates = Jinja2Templates(directory="templates")

# Global senkron zamanı
last_sync_time = None


# -------------------------------------------------
# HOME
# -------------------------------------------------
@app.get("/")
def home():
    return {"status": "running", "message": "VoorraadSync API actief 🎯"}


# -------------------------------------------------
# DASHBOARD
# -------------------------------------------------
@app.get("/woo/products/page/{page}")
def woo_products_page(page: int):
    """
    WooCommerce ürünlerini sayfalı şekilde döner
    """
    try:
        per_page = 20  # her sayfada 20 ürün göster

        all_products = woo_api.get_woo_products()

        total = len(all_products)
        total_pages = (total + per_page - 1) // per_page

        # sayfa aralığı kontrolü
        if page < 1 or page > total_pages:
            return {"error": "Geçersiz sayfa"}

        start = (page - 1) * per_page
        end = start + per_page

        return {
            "total": total,
            "total_pages": total_pages,
            "page": page,
            "per_page": per_page,
            "items": all_products[start:end]
        }

    except Exception as e:
        return {"error": str(e)}

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    global last_sync_time

    try:
        # WooCommerce ürünlerini çek
        products = woo_api.get_woo_products()

        # ürün sayısı
        total_products = len(products)

        # stok adeti 5’ten düşük olan ürünleri say
        low_stock = sum(
            1 for p in products
            if p.get("stock_quantity") is not None
            and int(p.get("stock_quantity")) < 5
        )

        # Eğer daha önce gerçek sync yapılmadıysa dashboard açılışını da senkron zamanı olarak göster
        if last_sync_time is None:
            last_sync_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    except Exception as e:
        print("Dashboard error:", e)
        products = []
        total_products = 0
        low_stock = 0
        if last_sync_time is None:
            last_sync_time = "WooCommerce bağlantı hatası"

    data = {
        "title": "VoorraadSync Dashboard",
        "total_products": total_products,
        "low_stock": low_stock,
        "last_sync": last_sync_time,
        "products": products,
    }

    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "data": data}
    )


# -------------------------------------------------
# WOOCOMMERCE ENDPOINTS
# -------------------------------------------------
@app.get("/woo/products")
def woo_products():
    return woo_api.get_woo_products()


@app.get("/woo/update_stock/{product_id}/{quantity}")
def update_woo_stock(product_id: int, quantity: int):
    """
    WooCommerce ürün stok güncelleme
    Dashboard'taki 'Kaydet' butonu buraya istek atıyor.
    """
    return woo_api.update_stock(product_id, quantity)


# -------------------------------------------------
# MANUEL SYNC (Woo -> Bol)
# -------------------------------------------------
@app.get("/sync")
def sync_now():
    """
    Sync Now butonu bu endpoint'i çağırır.
    Şu an sadece Woo'dan ürünleri çekip kaç ürün olduğunu döndürüyor.
    Bol Retailer API aktif olunca burada Bol stok güncellemesi açılır.
    """
    global last_sync_time

    try:
        products = woo_api.get_woo_products()

        # Bol API aktif olunca bu kısmı açacağız:
        #
        # for p in products:
        #     if p.get("id") and p.get("stock_quantity") is not None:
        #         bol_api.update_bol_stock(p["id"], p["stock_quantity"])

        last_sync_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return {
            "status": "ok",
            "message": "Senkron tamamlandı",
            "count": len(products),
            "last_sync": last_sync_time
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


# -------------------------------------------------
# BOL.COM ENDPOINTS
# -------------------------------------------------
@app.get("/bol/products")
def bol_products():
    return bol_api.get_bol_products()


@app.get("/bol/test_token")
def bol_test_token():
    return bol_api.get_access_token()


# -------------------------------------------------
# WOO → BOL WEBHOOK
# -------------------------------------------------
@app.post("/webhook/woo")
async def woo_webhook(data: dict):
    """
    WooCommerce webhook buraya POST atar.
    Ürün ID ve stok bilgisi ile Bol stok güncellemesi yapılır.
    """
    product_id = data.get("id")
    stock = data.get("stock_quantity")

    if not product_id or stock is None:
        return {"error": "Missing data"}

    bol_api.update_bol_stock(product_id, stock)

    return {"status": "ok"}
