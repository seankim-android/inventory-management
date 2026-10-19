"""
Tests for purchase order endpoints and the backlog purchase order flags.
"""
import re

import pytest


def payload(**overrides):
    body = {
        "backlog_item_id": "1",
        "supplier_name": "Acme Supply",
        "quantity": 350,
        "unit_cost": 12.5,
        "expected_delivery_date": "2025-11-15",
        "notes": "Rush order",
    }
    body.update(overrides)
    return body


def backlog_item(client, item_id):
    return next(b for b in client.get("/api/backlog").json() if b["id"] == item_id)


class TestPurchaseOrderEndpoints:
    """Test suite for /api/purchase-orders."""

    def test_create_purchase_order(self, client):
        response = client.post("/api/purchase-orders", json=payload())
        assert response.status_code == 201

        po = response.json()
        assert isinstance(po["id"], str) and po["id"]
        assert po["backlog_item_id"] == "1"
        assert po["supplier_name"] == "Acme Supply"
        assert po["quantity"] == 350
        assert po["unit_cost"] == 12.5
        assert po["expected_delivery_date"] == "2025-11-15"
        assert po["notes"] == "Rush order"
        assert po["status"] == "Pending"
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", po["created_date"])

    def test_create_without_notes(self, client):
        body = payload()
        del body["notes"]
        response = client.post("/api/purchase-orders", json=body)
        assert response.status_code == 201
        assert response.json()["notes"] is None

    def test_ids_are_unique(self, client):
        first = client.post("/api/purchase-orders", json=payload()).json()
        second = client.post("/api/purchase-orders", json=payload(backlog_item_id="2")).json()
        assert first["id"] != second["id"]

    def test_get_purchase_order(self, client):
        created = client.post("/api/purchase-orders", json=payload()).json()
        response = client.get("/api/purchase-orders/1")
        assert response.status_code == 200
        assert response.json() == created

    def test_get_returns_most_recent(self, client):
        client.post("/api/purchase-orders", json=payload(supplier_name="First"))
        second = client.post("/api/purchase-orders", json=payload(supplier_name="Second")).json()
        fetched = client.get("/api/purchase-orders/1").json()
        assert fetched["id"] == second["id"]
        assert fetched["supplier_name"] == "Second"

    def test_get_without_purchase_order_is_404(self, client):
        response = client.get("/api/purchase-orders/1")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_create_for_unknown_backlog_item_is_404(self, client):
        response = client.post("/api/purchase-orders", json=payload(backlog_item_id="999999"))
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
        assert client.get("/api/purchase-orders/999999").status_code == 404

    @pytest.mark.parametrize("field,value", [
        ("quantity", 0),
        ("quantity", -5),
        ("unit_cost", 0),
        ("unit_cost", -1.5),
        ("quantity", "many"),
    ])
    def test_create_validation_errors(self, client, field, value):
        response = client.post("/api/purchase-orders", json=payload(**{field: value}))
        assert response.status_code == 422
        assert field in response.json()["detail"][0]["loc"]
        assert client.get("/api/purchase-orders/1").status_code == 404

    def test_create_missing_required_field(self, client):
        body = payload()
        del body["supplier_name"]
        assert client.post("/api/purchase-orders", json=body).status_code == 422


class TestBacklogPurchaseOrderFlag:
    """The backlog endpoint reflects the in-memory purchase orders."""

    def test_flag_false_by_default(self, client):
        item = backlog_item(client, "1")
        assert item["has_purchase_order"] is False
        assert item["purchase_order_id"] is None

    def test_flag_set_after_create(self, client):
        po = client.post("/api/purchase-orders", json=payload(backlog_item_id="2")).json()
        with_po = backlog_item(client, "2")
        assert with_po["has_purchase_order"] is True
        assert with_po["purchase_order_id"] == po["id"]

        other = backlog_item(client, "1")
        assert other["has_purchase_order"] is False
        assert other["purchase_order_id"] is None

    def test_state_does_not_leak_between_tests(self, client):
        assert all(not b["has_purchase_order"] for b in client.get("/api/backlog").json())
