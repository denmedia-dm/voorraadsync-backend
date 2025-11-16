from fastapi import FastAPI, Request, Query
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from datetime import datetime
import json
import requests

import woo_api
import bol_api

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Global senkron zamanı
last_sync_time = None


# ----------------- Webhook Loglarını Oku -----------------
def read_webhook_logs(limit: int = 200):
    logs = []
    try:
        with open("webhook_logs.jsonl", "r") as f:
            lines = f.readlines()

        for line in reversed(lines[-limit:]):
            try:
                logs.append(json.loads(line))
            except:
                continue
    except FileNotFoundError:
        pass

    return logs


# ----------------- HOME -----------------
@app.get("/")
def home():
    return {"status": "running", "message": "VoorraadSync API actief 🎯"}


# ----------------- DASHBOARD -----------------
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    global last_sync_time

    try:
        # Sadece istatistik için tüm ürünleri çekiyoruz
        products = woo_api.get_woo_products()

        total_products = len(products)
        low_stock = sum(
            1 for p in products
            if p.get("stock_quantity") not in [None, ""] and int(p["stock_quantity"]) < 5
        )

        if last_sync_time is None:
            last_sync_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    except Exception as e:
        print("Dashboard error:", e)
        total_products = 0
        low_stock = 0
        last_sync_time = last_sync_time or "WooCommerce bağlantı hatası"

    data = {
        "title": "VoorraadSync Dashboard",
        "total_products": total_products,
        "low_stock": low_stock,
        "last_sync": last_sync_time,
    }

    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "data": data}
    )


# ----------------- WEBHOOK GERÇEK ZAMANLI LOG PANELİ -----------------
@app.get("/webhooks", response_class=HTMLResponse)
def webhooks_page(request: Request):
    logs = read_webhook_logs()
    data = {"title": "Webhook Logları"}

    return templates.TemplateResponse(
        "webhooks.html",
        {"request": request, "data": data, "logs": logs}
    )


# ----------------- WOO ENDPOINTLERİ -----------------
@app.get("/woo/products")
def woo_products():
    return woo_api.get_woo_products()


# -------- GERÇEK WOO API PAGINATION (TAVSİYE EDİLEN) --------
@app.get("/woo/products/page/{page}")
def woo_products_page(page: int, per_page: int = 50):
    """
    WooCommerce ürünlerini native pagination ile çeker.
    Tek seferde *gerçek* WooCommerce sayfası geliyor.
    Dashboard bu endpoint’i kullanır.
    """

    try:
        url = f"{woo_api.WC_URL}/wp-json/wc/v3/products"
        params = {
            "page": page,
            "per_page": per_page
        }

        response = requests.get(url, params=params, auth=(woo_api.WC_KEY, woo_api.WC_SECRET))
        items = response.json()

        total_pages = int(response.headers.get("X-WP-TotalPages", 1))
        total_items = int(response.headers.get("X-WP-Total", len(items)))

        return {
            "page": page,
            "per_page": per_page,
            "total_pages": total_pages,
            "total_items": total_items,
            "items": items,
        }

    except Exception as e:
        return {"error": str(e)}



@app.get("/woo/update_stock/{product_id}/{quantity}")
def update_woo_stock(product_id: int, quantity: int):
    return woo_api.update_stock(product_id, quantity)


# ----------------- MANUEL SYNC -----------------
@app.get("/sync")
def sync_now():
    global last_sync_time

    try:
        products = woo_api.get_woo_products()
        last_sync_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return {
            "status": "ok",
            "message": "Senkron tamamlandı",
            "count": len(products),
            "last_sync": last_sync_time
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}



# ----------------- BOL ENDPOINTLERİ -----------------
@app.get("/bol/products")
def bol_products():
    return bol_api.get_bol_products()


@app.get("/bol/test_token")
def bol_test_token():
    return bol_api.get_access_token()



# ----------------- WEBHOOK JSON API -----------------
@app.get("/webhooks/logs")
def get_webhook_logs(limit: int = 200):
    logs = read_webhook_logs(limit)
    return {"logs": logs}



# ----------------- WOO → BOL WEBHOOK -----------------
@app.post("/webhook/woo")
async def woo_webhook(data: dict):
    """
    WooCommerce bu endpoint'e POST gönderir.
    Biz burada hem log kaydediyoruz hem de Bol senkronu tetikleyebiliriz.
    """

    product_id = data.get("id")
    stock = data.get("stock_quantity")

    # ---- LOG KAYDI ----
    log_entry = {
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "source": "woocommerce",
        "event": "product.updated",
        "product_id": product_id,
        "stock": stock,
        "raw": data,
    }

    try:
        with open("webhook_logs.jsonl", "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except:
        pass

    # Veri eksikse dön
    if not product_id:
        return {"error": "Missing product_id"}

    # Bol stok güncelle (API aktif olduğunda)
    try:
        bol_api.update_bol_stock(product_id, stock)
    except Exception as e:
        print("Bol update error:", e)

    return {"status": "ok"}

import csv
from fastapi.responses import StreamingResponse
from io import StringIO

@app.get("/export/csv")
def export_csv():
    """
    WooCommerce ürünlerini CSV olarak export eder.
    """
    try:
        products = woo_api.get_woo_products()

        # CSV buffer
        csv_buffer = StringIO()
        writer = csv.writer(csv_buffer)

        # CSV header
        writer.writerow([
            "ID", "Name", "SKU", "Stock", "Price", "Status", "Type"
        ])

        # Data rows
        for p in products:
            writer.writerow([
                p.get("id"),
                p.get("name"),
                p.get("sku"),
                p.get("stock_quantity"),
                p.get("price"),
                p.get("status"),
                p.get("type"),
            ])

        csv_buffer.seek(0)

        return StreamingResponse(
            csv_buffer,
            media_type="text/csv",
            headers={
                "Content-Disposition": "attachment; filename=woocommerce_products.csv"
            }
        )

    except Exception as e:
        return {"error": str(e)}
