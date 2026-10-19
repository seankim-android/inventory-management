"""
Tests for orders and reports API endpoints.
"""
import json
from collections import Counter
from pathlib import Path

import pytest

ORDERS_FILE = Path(__file__).parent.parent.parent / "server" / "data" / "orders.json"
QUARTERS = {
    "Q1-2025": ("2025-01", "2025-02", "2025-03"),
    "Q2-2025": ("2025-04", "2025-05", "2025-06"),
    "Q3-2025": ("2025-07", "2025-08", "2025-09"),
    "Q4-2025": ("2025-10", "2025-11", "2025-12"),
}


@pytest.fixture(scope="module")
def all_orders():
    return json.loads(ORDERS_FILE.read_text())


class TestOrdersEndpoints:
    """Test suite for /api/orders."""

    def test_get_all_orders(self, client, all_orders):
        data = client.get("/api/orders").json()
        assert len(data) == len(all_orders) == 250
        first = data[0]
        for field in ("id", "order_number", "customer", "items", "status", "order_date",
                      "expected_delivery", "total_value"):
            assert field in first

    def test_order_ids_and_numbers_unique(self, client):
        data = client.get("/api/orders").json()
        ids = Counter(o["id"] for o in data)
        numbers = Counter(o["order_number"] for o in data)
        assert [k for k, v in ids.items() if v > 1] == []
        assert [k for k, v in numbers.items() if v > 1] == []

    def test_order_number_matches_id(self, client):
        for order in client.get("/api/orders").json():
            assert order["order_number"] == f"ORD-2025-{int(order['id']):04d}"

    def test_filter_by_warehouse(self, client, all_orders):
        data = client.get("/api/orders?warehouse=Tokyo").json()
        expected = [o for o in all_orders if o["warehouse"] == "Tokyo"]
        assert len(data) == len(expected) > 0
        assert all(o["warehouse"] == "Tokyo" for o in data)

    def test_filter_by_category(self, client, all_orders):
        data = client.get("/api/orders?category=Sensors").json()
        expected = [o for o in all_orders if o["category"].lower() == "sensors"]
        assert len(data) == len(expected) > 0
        assert all(o["category"].lower() == "sensors" for o in data)

    def test_filter_by_status(self, client, all_orders):
        data = client.get("/api/orders?status=Delivered").json()
        expected = [o for o in all_orders if o["status"].lower() == "delivered"]
        assert len(data) == len(expected) > 0
        assert all(o["status"].lower() == "delivered" for o in data)

    def test_filter_all_means_no_filter(self, client):
        data = client.get("/api/orders?warehouse=all&category=all&status=all&month=all").json()
        assert len(data) == 250

    def test_filter_combined(self, client, all_orders):
        data = client.get("/api/orders?warehouse=Tokyo&status=Delivered&month=2025-01").json()
        expected = [o for o in all_orders if o["warehouse"] == "Tokyo"
                    and o["status"].lower() == "delivered" and o["order_date"].startswith("2025-01")]
        assert sorted(o["id"] for o in data) == sorted(o["id"] for o in expected)

    def test_filter_by_month_exact(self, client, all_orders):
        data = client.get("/api/orders?month=2025-03").json()
        expected = [o for o in all_orders if o["order_date"].startswith("2025-03")]
        assert len(data) == len(expected) > 0
        assert all(o["order_date"].startswith("2025-03") for o in data)

    def test_month_partial_value_is_rejected(self, client):
        """Regression: ?month=2025-1 used to substring-match Jan, Oct, Nov and Dec."""
        for value in ("2025-1", "-", "2025", "2025-13x", "Q5-2025", "garbage"):
            response = client.get("/api/orders", params={"month": value})
            assert response.status_code == 400, value
            assert "invalid month" in response.json()["detail"].lower()

    def test_month_filter_does_not_leak_other_months(self, client):
        january = client.get("/api/orders?month=2025-01").json()
        october = client.get("/api/orders?month=2025-10").json()
        assert january and october
        assert {o["id"] for o in january}.isdisjoint({o["id"] for o in october})

    @pytest.mark.parametrize("quarter", sorted(QUARTERS))
    def test_filter_by_quarter(self, client, all_orders, quarter):
        data = client.get(f"/api/orders?month={quarter}").json()
        expected = [o for o in all_orders if o["order_date"].startswith(QUARTERS[quarter])]
        assert len(data) == len(expected) > 0
        assert all(o["order_date"].startswith(QUARTERS[quarter]) for o in data)

    def test_quarter_is_case_insensitive(self, client):
        upper = client.get("/api/orders?month=Q1-2025").json()
        lower = client.get("/api/orders?month=q1-2025").json()
        assert upper and [o["id"] for o in lower] == [o["id"] for o in upper]

    def test_dashboard_summary_validates_month(self, client):
        assert client.get("/api/dashboard/summary?month=Q5-2025").status_code == 400
        assert client.get("/api/dashboard/summary?month=2025-1").status_code == 400
        assert client.get("/api/dashboard/summary?month=Q1-2025").status_code == 200
        assert client.get("/api/dashboard/summary?month=q1-2025").status_code == 200

    def test_get_order_by_id(self, client, all_orders):
        response = client.get("/api/orders/201")
        assert response.status_code == 200
        order = response.json()
        assert order["id"] == "201"
        assert order["order_number"] == "ORD-2025-0201"
        assert order["customer"] == next(o for o in all_orders if o["id"] == "201")["customer"]

    def test_get_renumbered_order(self, client):
        order = client.get("/api/orders/251").json()
        assert order["order_number"] == "ORD-2025-0251"

    def test_get_nonexistent_order(self, client):
        response = client.get("/api/orders/does-not-exist")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestReportsEndpoints:
    """Test suite for /api/reports/*."""

    def test_quarterly_report(self, client, all_orders):
        data = client.get("/api/reports/quarterly").json()
        assert [q["quarter"] for q in data] == sorted(QUARTERS)
        for report in data:
            orders = [o for o in all_orders if o["order_date"].startswith(QUARTERS[report["quarter"]])]
            delivered = [o for o in orders if o["status"] == "Delivered"]
            revenue = sum(o["total_value"] for o in orders)
            assert report["total_orders"] == len(orders)
            assert report["delivered_orders"] == len(delivered)
            assert report["total_revenue"] == pytest.approx(revenue)
            assert report["avg_order_value"] == pytest.approx(revenue / len(orders), abs=0.01)
            assert report["fulfillment_rate"] == pytest.approx(len(delivered) / len(orders) * 100, abs=0.05)

    def test_quarterly_totals_match_orders(self, client):
        quarterly = client.get("/api/reports/quarterly").json()
        orders = client.get("/api/orders").json()
        assert sum(q["total_orders"] for q in quarterly) == len(orders)
        assert sum(q["total_revenue"] for q in quarterly) == pytest.approx(sum(o["total_value"] for o in orders))

    def test_monthly_trends(self, client, all_orders):
        data = client.get("/api/reports/monthly-trends").json()
        months = [m["month"] for m in data]
        assert months == sorted(set(months))
        assert set(months) == {o["order_date"][:7] for o in all_orders}
        for entry in data:
            orders = [o for o in all_orders if o["order_date"].startswith(entry["month"])]
            assert entry["order_count"] == len(orders)
            assert entry["delivered_count"] == sum(1 for o in orders if o["status"] == "Delivered")
            assert entry["revenue"] == pytest.approx(sum(o["total_value"] for o in orders))

    def test_monthly_trends_consistent_with_quarterly(self, client):
        monthly = client.get("/api/reports/monthly-trends").json()
        quarterly = client.get("/api/reports/quarterly").json()
        assert sum(m["order_count"] for m in monthly) == sum(q["total_orders"] for q in quarterly) == 250
        assert sum(m["revenue"] for m in monthly) == pytest.approx(sum(q["total_revenue"] for q in quarterly))
