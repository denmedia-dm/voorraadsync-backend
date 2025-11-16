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
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    global last_sync_time

    try:
        # WooCommerce ürünlerini çek
        products = woo_api.get_woo_products()

        # ürün sayısı
        total_products = len(products)

        # stok adeti 5’ten düşük olan ürünleri say
        low_stock = sum(1 for p in products if int(p.get("stock_quantity", 9999)) < 5)

        # senkron zamanını güncelle
        last_sync_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    except Exception as e:
        print("Dashboard error:", e)
        total_products = 0
        low_stock = 0
        last_sync_time = "WooCommerce bağlantı hatası"

    data = {
        "title": "VoorraadSync Dashboard",
        "total_products": total_products,
        "low_stock": low_stock,
        "last_sync": last_sync_time
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
    return woo_api.update_stock(product_id, quantity)


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
    product_id = data.get("id")
    stock = data.get("stock_quantity")

    if not product_id or stock is None:
        return {"error": "Missing data"}

    bol_api.update_bol_stock(product_id, stock)

    return {"status": "ok"}
