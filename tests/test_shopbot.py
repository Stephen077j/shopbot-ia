import json

import pytest
from fastapi.testclient import TestClient

from app import catalog
from app.bot import execute_tool
from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_products_endpoint():
    r = client.get("/api/products")
    assert r.status_code == 200
    assert len(r.json()) >= 5


def test_search_products():
    assert len(catalog.search_products()) == len(catalog.PRODUCTS)
    results = catalog.search_products(query="café")
    assert len(results) == 1
    assert results[0]["name"] == "Café Arabica 250g"
    assert len(catalog.search_products(category="artisanat")) == 2


def test_create_order_and_stock():
    product = catalog.get_product(1)
    initial_stock = product["stock"]
    order = catalog.create_order(1, 2, "Rakoto", "034 12 345 67")
    assert order["total"] == product["price"] * 2
    assert product["stock"] == initial_stock - 2
    assert order["status"] == "en attente de confirmation"


def test_create_order_validations():
    with pytest.raises(ValueError, match="introuvable"):
        catalog.create_order(999, 1, "X", "034")
    with pytest.raises(ValueError, match="positive"):
        catalog.create_order(1, 0, "X", "034")
    with pytest.raises(ValueError, match="Stock insuffisant"):
        catalog.create_order(5, 9999, "X", "034")


def test_execute_tool_search():
    result = json.loads(execute_tool("search_products", {"query": "vanille"}))
    assert result[0]["name"].startswith("Vanille")


def test_execute_tool_error_is_json():
    result = json.loads(execute_tool("create_order", {"product_id": 999, "quantity": 1,
                                                      "customer_name": "X", "customer_phone": "0"}))
    assert "error" in result


def test_chat_requires_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    r = client.post("/api/chat", json={"session_id": "t", "message": "salut"})
    assert r.status_code == 503


def test_whatsapp_webhook_verification():
    r = client.get("/webhook/whatsapp", params={
        "hub.mode": "subscribe", "hub.verify_token": "shopbot-verify", "hub.challenge": "12345",
    })
    assert r.status_code == 200
    assert r.text == "12345"

    r = client.get("/webhook/whatsapp", params={
        "hub.mode": "subscribe", "hub.verify_token": "mauvais", "hub.challenge": "12345",
    })
    assert r.status_code == 403


def test_whatsapp_webhook_ignores_non_text():
    r = client.post("/webhook/whatsapp", json={"entry": []})
    assert r.status_code == 200
    assert r.json()["status"] == "ignored"
