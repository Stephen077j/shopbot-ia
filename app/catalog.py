"""Catalogue produits et commandes (démo en mémoire — remplacer par une vraie BDD en production)."""
import itertools
from datetime import datetime

PRODUCTS = [
    {"id": 1, "name": "T-shirt coton bio", "price": 45000, "stock": 24, "category": "vêtements"},
    {"id": 2, "name": "Sac artisanal en raphia", "price": 85000, "stock": 10, "category": "artisanat"},
    {"id": 3, "name": "Café Arabica 250g", "price": 28000, "stock": 50, "category": "alimentation"},
    {"id": 4, "name": "Vanille Bourbon 10 gousses", "price": 60000, "stock": 35, "category": "alimentation"},
    {"id": 5, "name": "Chapeau tressé", "price": 38000, "stock": 8, "category": "artisanat"},
    {"id": 6, "name": "Huile essentielle Ravintsara 30ml", "price": 42000, "stock": 15, "category": "bien-être"},
]

_order_seq = itertools.count(1)
ORDERS: list[dict] = []


def search_products(query: str = "", category: str = "") -> list[dict]:
    results = PRODUCTS
    if category:
        results = [p for p in results if category.lower() in p["category"].lower()]
    if query:
        results = [p for p in results if query.lower() in p["name"].lower()]
    return results


def get_product(product_id: int) -> dict | None:
    return next((p for p in PRODUCTS if p["id"] == product_id), None)


def create_order(product_id: int, quantity: int, customer_name: str, customer_phone: str) -> dict:
    product = get_product(product_id)
    if not product:
        raise ValueError(f"Produit {product_id} introuvable")
    if quantity <= 0:
        raise ValueError("La quantité doit être positive")
    if product["stock"] < quantity:
        raise ValueError(f"Stock insuffisant : {product['stock']} restant(s)")
    product["stock"] -= quantity
    order = {
        "id": next(_order_seq),
        "product": product["name"],
        "quantity": quantity,
        "total": product["price"] * quantity,
        "customer_name": customer_name,
        "customer_phone": customer_phone,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "status": "en attente de confirmation",
    }
    ORDERS.append(order)
    return order
