from fastapi import FastAPI
import woo_api
import bol_api

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
