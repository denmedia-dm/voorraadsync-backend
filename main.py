from fastapi import FastAPI
from bol_api import get_bol_products
from woo_api import get_woo_products, update_woo_stock

app = FastAPI(title="VoorraadSync", description="Bol.com en WooCommerce voorraad synchronisatie", version="1.0")

@app.get("/")
def home():
    return {"status": "running", "message": "VoorraadSync API actief 🎯"}

@app.get("/woo/products")
def woo_products():
    return get_woo_products()

@app.get("/woo/update_stock/{product_id}/{quantity}")
def update_woo_stock(product_id: int, quantity: int):
    return woo_api.update_stock(product_id, quantity)

@app.get("/bol/products")
def bol_products():
    return get_bol_products()

@app.put("/woo/update_stock/{product_id}/{new_stock}")
def update_stock(product_id: int, new_stock: int):
    return update_woo_stock(product_id, new_stock)
