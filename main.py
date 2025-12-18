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
        # 1️⃣ WooCommerce toplam ürün sayısı (sadece ilk sayfa, hızlı)
        first_page = woo_api.get_woo_products(page=1, per_page=50)

        total_products = first_page.get("total_items", 0)

        # 2️⃣ GERÇEK low-stock raporu (TÜM ürünlerden)
        low_stock_response = requests.get(
            request.url_for("low_stock_report"),
            params={"threshold": 5}
        ).json()

        critical_stock = low_stock_response.get("total_critical", 0)
        warning_stock = low_stock_response.get("total_warning", 0)

        if last_sync_time is None:
            last_sync_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    except Exception as e:
        print("Dashboard error:", e)
        total_products = 0
        critical_stock = 0
        warning_stock = 0
        if last_sync_time is None:
            last_sync_time = "WooCommerce bağlantı hatası"

    # 3️⃣ Dashboard’a gönderilen data
    data = {
        "title": "VoorraadSync Dashboard",
        "total_products": total_products,
        "low_stock": critical_stock + warning_stock,
        "critical_stock": critical_stock,
        "warning_stock": warning_stock,
        "last_sync": last_sync_time,
    }

    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "data": data}
    )


# ----------------- WEBHOOK PANEL -----------------
@app.get("/webhooks", response_class=HTMLResponse)
def webhooks_page(request: Request):
    logs = read_webhook_logs()
    data = {"title": "Webhook Logları"}

    return templates.TemplateResponse(
        "webhooks.html",
        {"request": request, "data": data, "logs": logs}
    )

# ----------------- LOW STOCK REPORT -----------------
@app.get("/reports/low-stock")
def low_stock_report(threshold: int = 5):
    """
    Tüm WooCommerce ürünlerini tarar.
    threshold altındaki stokları döner.
    """

    try:
        critical = []  # stok = 0
        warning = []   # stok 1–threshold

        page = 1
        per_page = 100

        while True:
            result = woo_api.get_woo_products(page=page, per_page=per_page)
            items = result.get("items", [])

            if not items:
                break

            for p in items:
                stock = p.get("stock_quantity")

                if stock is None:
                    continue

                stock = int(stock)

                if stock == 0:
                    critical.append(p)
                elif stock <= threshold:
                    warning.append(p)

            page += 1

        return {
            "critical": critical,
            "warning": warning,
            "total_critical": len(critical),
            "total_warning": len(warning),
            "threshold": threshold
        }

    except Exception as e:
        return {"error": str(e)}

# ----------------- WOO ENDPOINTLERİ -----------------
@app.get("/woo/products/page/{page}")
def woo_products_page(page: int, per_page: int = 50):
    """
    WooCommerce ürünlerini gerçek WooCommerce pagination ile getirir.
    """
    try:
        result = woo_api.get_woo_products(page=page, per_page=per_page)

        if "error" in result:
            return result

        return result

    except Exception as e:
        return {"error": str(e)}


@app.get("/woo/update_stock/{product_id}/{quantity}")
def update_woo_stock(product_id: int, quantity: int):
    return woo_api.update_stock(product_id, quantity)

# ----------------- RAPORLAR -----------------
@app.get("/reports/low-stock")
def low_stock_report():
    """
    Stok < 5 olan ürünleri döner
    - critical: 0–1
    - warning: 2–4
    """
    try:
        # İlk etapta performans için ilk 500 ürünü alıyoruz
        result = woo_api.get_woo_products(page=1, per_page=500)
        items = result.get("items", [])

        critical = []
        warning = []

        for p in items:
            stock = p.get("stock_quantity")

            if stock is None:
                continue

            try:
                stock = int(stock)
            except:
                continue

            product_data = {
                "id": p.get("id"),
                "name": p.get("name"),
                "sku": p.get("sku"),
                "stock": stock,
            }

            if stock <= 1:
                critical.append(product_data)
            elif stock <= 4:
                warning.append(product_data)

        return {
            "critical": critical,
            "warning": warning,
            "total_critical": len(critical),
            "total_warning": len(warning),
        }

    except Exception as e:
        return {"error": str(e)}

# ----------------- MANUEL SYNC -----------------
@app.get("/sync")
def sync_now():
    global last_sync_time

    try:
        page1 = woo_api.get_woo_products(page=1, per_page=50)
        last_sync_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return {
            "status": "ok",
            "message": "Senkron tamamlandı",
            "count": page1.get("total_items", 0),
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

    if not product_id:
        return {"error": "Missing product_id"}

    try:
        bol_api.update_bol_stock(product_id, stock)
    except Exception as e:
        print("Bol update error:", e)

    return {"status": "ok"}


# ----------------- CSV EXPORT -----------------
import csv
from fastapi.responses import StreamingResponse
from io import StringIO

@app.get("/export/csv")
def export_csv():
    try:
        products = woo_api.get_woo_products(page=1, per_page=500)["items"]

        csv_buffer = StringIO()
        writer = csv.writer(csv_buffer)

        writer.writerow(["ID", "Name", "SKU", "Stock", "Price", "Status", "Type"])

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
            headers={"Content-Disposition": "attachment; filename=products.csv"}
        )

    except Exception as e:
        return {"error": str(e)}

@app.get("/reports/low-stock")
def low_stock_report(threshold: int = 5):
    """
    Tüm WooCommerce ürünlerini tarar
    Kritik ve uyarı stoklarını döner
    """

    critical = []
    warning = []

    page = 1
    per_page = 100  # Woo max

    while True:
        result = woo_api.get_woo_products(page=page, per_page=per_page)

        items = result.get("items", [])
        if not items:
            break

        for p in items:
            stock = p.get("stock_quantity")

            if stock is None:
                continue

            stock = int(stock)

            product_info = {
                "id": p.get("id"),
                "name": p.get("name"),
                "sku": p.get("sku"),
                "stock": stock
            }

            if stock == 0:
                critical.append(product_info)
            elif 0 < stock <= threshold:
                warning.append(product_info)

        page += 1

    return {
        "threshold": threshold,
        "critical": critical,
        "warning": warning,
        "total_critical": len(critical),
        "total_warning": len(warning)
    }
# ----------------- BOL AUTH TEST -----------------
@app.get("/bol/auth/test")
def bol_auth_test():
    try:
        token = bol_api.get_access_token()
        return {
            "status": "ok",
            "token_preview": token[:20] + "..."
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }