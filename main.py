from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, StreamingResponse
from datetime import datetime
from io import StringIO
import json
import csv

import woo_api
import bol_api

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Global senkron zamanı (RAM'de)
last_sync_time = None


# ----------------- Yardımcı: Webhook Loglarını Oku -----------------
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


# ----------------- DASHBOARD (HTML ONLY - HIZLI AÇILIR) -----------------
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    # Woo çağırmıyoruz -> sayfa anında açılır
    data = {
        "title": "VoorraadSync Dashboard",
        "total_products": "...",
        "low_stock": "...",
        "last_sync": "Yükleniyor..."
    }
    return templates.TemplateResponse("dashboard.html", {"request": request, "data": data})


# ----------------- DASHBOARD STATS API (LAZY LOAD) -----------------
@app.get("/api/dashboard/stats")
def dashboard_stats(threshold: int = 5):
    """
    Dashboard kartları için hızlı istatistik.
    - total_products: Woo total
    - low_stock: tüm ürünlerden hesaplanır (tüm sayfaları dolaşır)
    """
    global last_sync_time

    try:
        # total ürün sayısını header/metadata üzerinden almak için:
        page1 = woo_api.get_woo_products(page=1, per_page=50)
        total_products = page1.get("total_items", 0)

        # GERÇEK low-stock: tüm sayfalardan hesapla
        critical_count = 0
        warning_count = 0

        page = 1
        per_page = 100

        while True:
            result = woo_api.get_woo_products(page=page, per_page=per_page)
            items = result.get("items", [])
            if not items:
                break

            for p in items:
                stock = p.get("stock_quantity")
                if stock in [None, ""]:
                    continue
                try:
                    stock_i = int(stock)
                except:
                    continue

                if stock_i == 0:
                    critical_count += 1
                elif 0 < stock_i < threshold:
                    warning_count += 1

            page += 1

        return {
            "total_products": total_products,
            "low_stock": critical_count + warning_count,
            "critical_stock": critical_count,
            "warning_stock": warning_count,
            "threshold": threshold,
            "last_sync": last_sync_time or "Henüz senkron yok"
        }

    except Exception as e:
        return {"error": True, "message": str(e)}


# ----------------- WEBHOOK PANEL (HTML) -----------------
@app.get("/webhooks", response_class=HTMLResponse)
def webhooks_page(request: Request):
    logs = read_webhook_logs()
    data = {"title": "Webhook Logları"}
    return templates.TemplateResponse("webhooks.html", {"request": request, "data": data, "logs": logs})


# ----------------- WEBHOOK LOG JSON API -----------------
@app.get("/webhooks/logs")
def get_webhook_logs(limit: int = 200):
    logs = read_webhook_logs(limit)
    return {"logs": logs}


# ----------------- LOW STOCK REPORT (JSON) -----------------
@app.get("/reports/low-stock")
def low_stock_report(threshold: int = 5, limit: int = 50):
    """
    Tüm Woo ürünlerini tarar:
    - critical: stok == 0
    - warning: 0 < stok < threshold   (örn threshold=5 => 1..4)
    limit: listeyi şişirmemek için dönen item sayısı (UI için)
    """
    try:
        critical = []
        warning = []

        page = 1
        per_page = 100

        while True:
            result = woo_api.get_woo_products(page=page, per_page=per_page)
            items = result.get("items", [])
            if not items:
                break

            for p in items:
                stock = p.get("stock_quantity")
                if stock in [None, ""]:
                    continue

                try:
                    stock_i = int(stock)
                except:
                    continue

                info = {
                    "id": p.get("id"),
                    "name": p.get("name"),
                    "sku": p.get("sku"),
                    "stock_quantity": stock_i
                }

                if stock_i == 0:
                    if len(critical) < limit:
                        critical.append(info)
                elif 0 < stock_i < threshold:
                    if len(warning) < limit:
                        warning.append(info)

            page += 1

        # Not: total sayımı için limit dışını da saymak istersen,
        # ayrı counter ekleriz. Şimdilik UI için yeterli.
        return {
            "threshold": threshold,
            "critical": critical,
            "warning": warning,
            "total_critical": len(critical),
            "total_warning": len(warning)
        }

    except Exception as e:
        return {"error": str(e)}


# ----------------- WOO ENDPOINTLERİ -----------------
@app.get("/woo/products/page/{page}")
def woo_products_page(page: int, per_page: int = 50):
    """
    Dashboard tablo + mobil kartlar bu endpoint'i kullanır.
    """
    try:
        result = woo_api.get_woo_products(page=page, per_page=per_page)
        return result
    except Exception as e:
        return {"error": str(e)}


@app.get("/woo/update_stock/{product_id}/{quantity}")
def update_woo_stock(product_id: int, quantity: int):
    return woo_api.update_stock(product_id, quantity)


# ----------------- MANUEL SYNC -----------------
@app.get("/sync")
def sync_now():
    """
    Şimdilik sadece last_sync_time güncelliyoruz.
    (Bol aktif olunca burada Woo -> Bol güncelleme çalışacak)
    """
    global last_sync_time

    try:
        # hafif kontrol
        _ = woo_api.get_woo_products(page=1, per_page=1)
        last_sync_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return {
            "status": "ok",
            "message": "Senkron zamanı güncellendi",
            "last_sync": last_sync_time
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}


# ----------------- CSV EXPORT -----------------
@app.get("/export/csv")
def export_csv():
    """
    Basit CSV export.
    Not: 500 sınırı var. İstersen gerçek pagination ile tümünü export edecek hale getiririz.
    """
    try:
        products = woo_api.get_woo_products(page=1, per_page=500).get("items", [])

        csv_buffer = StringIO()
        writer = csv.writer(csv_buffer)

        writer.writerow(["ID", "Name", "SKU", "Stock", "Price", "Status", "Type"])

        for p in products:
            writer.writerow([
                p.get("id"),
                p.get("name"),
                p.get("sku"),
                p.get("stock_quantity"),
                p.get("price") or p.get("regular_price"),
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


# ----------------- BOL ENDPOINTLERİ -----------------
@app.get("/bol/products")
def bol_products():
    return bol_api.get_bol_products()


@app.get("/bol/test_token")
def bol_test_token():
    return bol_api.get_access_token()


# ----------------- BOL AUTH TEST -----------------
@app.get("/bol/auth/test")
def bol_auth_test():
    try:
        token = bol_api.get_access_token()
        return {"status": "ok", "token_preview": token[:20] + "..."}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ----------------- WOO → BOL WEBHOOK -----------------
@app.post("/webhook/woo")
async def woo_webhook(data: dict):
    """
    WooCommerce webhook buraya POST atar.
    Log alırız. Bol aktif olunca burada güncelleme tetiklenir.
    """
    product_id = data.get("id")
    stock = data.get("stock_quantity")

    # LOG
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

    # Bol güncelle (şimdilik deneme)
    try:
        bol_api.update_bol_stock(product_id, stock)
    except Exception as e:
        print("Bol update error:", e)

    return {"status": "ok"}