from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

import woo_api
import bol_api

app = FastAPI()

templates = Jinja2Templates(directory="templates")


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    data = {
        "title": "VoorraadSync Dashboard",
        "total_products": 0,
        "low_stock": 0,
        "last_sync": "Henüz senkron yapılmadı"
    }

    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "data": data}
    )
    
app = FastAPI()

@app.get("/")
def home():
    return {"status": "running", "message": "VoorraadSync API actief 🎯"}

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
