from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from datetime import datetime
import json

import woo_api
import bol_api

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Global senkron zamanı
last_sync_time = None


# ----------------- Yardımcı: Webhook loglarını oku -----------------
def read_webhook_logs(limit: int = 100):
    logs = []
    try:
        with open("webhook_logs.jsonl", "r") as f:
            lines = f.readlines()

        # En son gelenleri tersten al
        for line in reversed(lines[-limit:]):
            try:
                logs.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    except FileNotFoundError:
        # log dosyası yoksa boş liste dön
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
        products = woo_api.get_woo_products()

        total_products = len(products)
        low_stock = sum(
            1 for p in products
            if p.get("stock_quantity") is not None
            and int(p.get("stock_quantity")) < 5
        )

        if last_sync_time is None:
            last_sync_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    except Exception as e:
        print("Dashboard error:", e)
        total_products = 0
        low_stock = 0
        if last_sync_time is None:
            last_sync_time = "WooCommerce bağlantı hatası"

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


# ----------------- WEBHOOK PANEL (HTML) -----------------
@app.get("/webhooks", response_class=HTMLResponse)
def webhooks_page(request: Request):
    logs = read_webhook_logs()
    data = {"title": "Webhook Logları"}

    return templates.TemplateResponse(
        "webhooks.html",
        {"request": request, "data": data, "logs": logs}
    )


# ----------------- WOOCOMMERCE ENDPOINTLERİ -----------------
@app.get("/woo/products")
def woo_products():
    return woo_api.get_woo_products()


@app.get("/woo/products/page/{page}")
def woo_products_page(page: int):
    """
    Dashboard tablosu için sayfalı ürün listesi
    """
    try:
        per_page = 20
        all_products = woo_api.get_woo_products()

        total = len(all_products)
        total_pages = (total + per_page - 1) // per_page or 1

        if page < 1 or page > total_pages:
            return {"error": "Geçersiz sayfa"}

        start = (page - 1) * per_page
        end = start + per_page

        return {
            "total": total,
            "total_pages": total_pages,
            "page": page,
            "per_page": per_page,
            "items": all_products[start:end],
        }

    except Exception as e:
        return {"error": str(e)}


@app.get("/woo/update_stock/{product_id}/{quantity}")
def update_woo_stock(product_id: int, quantity: int):
    """
    Dashboard'taki 'Kaydet' butonu Woo stok güncellemesi için burayı kullanıyor.
    """
    return woo_api.update_stock(product_id, quantity)


# ----------------- MANUEL SYNC (Woo -> Bol hazırlık) -----------------
@app.get("/sync")
def sync_now():
    """
    Sync Now butonu burayı çağırıyor.
    Şimdilik sadece Woo'dan ürün sayısını çekip last_sync_time güncelliyor.
    Bol Retailer API aktif olunca burada Bol stok güncellemesi açılacak.
    """
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


# ----------------- BOL.COM ENDPOINTLERİ -----------------
@app.get("/bol/products")
def bol_products():
    return bol_api.get_bol_products()


@app.get("/bol/test_token")
def bol_test_token():
    return bol_api.get_access_token()


# ----------------- WEBHOOK LOG JSON API -----------------
@app.get("/webhooks/logs")
def get_webhook_logs(limit: int = 100):
    """
    İstersen ileride frontend'ten de JSON olarak webhook loglarını çekebilirsin.
    Şu an webhooks.html içindeki tablo read_webhook_logs() fonksiyonunu kullanıyor.
    """
    logs = read_webhook_logs(limit)
    return {"logs": logs}


# ----------------- WOO → BOL WEBHOOK (LOG İLE) -----------------
@app.post("/webhook/woo")
async def woo_webhook(data: dict):
    """
    WooCommerce webhook buraya POST atar.
    Hem log kaydediyoruz, hem de (mümkün olduğunda) Bol stok güncellemesi burada yapılacak.
    """

    product_id = data.get("id")
    stock = data.get("stock_quantity")

    # 1) LOG KAYDI
    log_entry = {
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "source": "woocommerce",
        "event": "stock_update",
        "product_id": product_id,
        "stock": stock,
        "raw": data,
    }

    try:
        with open("webhook_logs.jsonl", "a") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        print("Webhook log yazılamadı:", e)

    # 2) Veri eksikse hemen dön
    if not product_id or stock is None:
        return {"error": "Missing data"}

    # 3) (Şimdilik) Bol güncelleme denemesi - Retailer API tamamen açılınca netleştireceğiz
    try:
        bol_api.update_bol_stock(product_id, stock)
    except Exception as e:
        print("Bol update error:", e)

    return {"status": "ok"}
