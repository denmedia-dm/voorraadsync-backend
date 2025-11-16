from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

import woo_api
import bol_api

app = FastAPI()

templates = Jinja2Templates(directory="templates")

@app.get("/")
def home():
    return {"status": "running", "message": "VoorraadSync API actief 🎯"}

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):

    # WooCommerce ürünlerini çek
    try:
        products = woo_api.get_woo_products()

        # ürün listesi array ise:
        total_products = len(products)

        # stok adeti 5’ten düşük olanları say
        low_stock = len([p for p in products if p.get("stock_quantity", 9999) < 5])

        last_sync = "Henüz senkron yapılmadı"

    except Exception as e:
        print("Dashboard error:", e)
        total_products = 0
        low_stock = 0
        last_sync = "WooCommerce bağlantı hatası"

    data = {
        "title": "VoorraadSync Dashboard",
        "total_products": total_products,
        "low_stock": low_stock,
        "last_sync": last_sync
    }

    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "data": data}
    )

# --- WooCommerce Endpoints ---
@app.get("/woo/products")
def woo_products():
    return woo_api.get_woo_products()

@app.get("/woo/update_stock/{product_id}/{quantity}")
def update_woo_stock(product_id: int, quantity: int):
    return woo_api.update_stock(product_id, quantity)

# --- Bol.com Endpoints ---
@app.get("/bol/products")
def bol_products():
    return bol_api.get_bol_products()

@app.get("/bol/test_token")
def bol_test_token():
    return bol_api.get_access_token()

@app.post("/webhook/woo")
async def woo_webhook(data: dict):
    product_id = data.get("id")
    stock = data.get("stock_quantity")

    if not product_id or stock is None:
        return {"error": "Missing data"}

    bol_api.update_bol_stock(product_id, stock)

    return {"status": "ok"}
