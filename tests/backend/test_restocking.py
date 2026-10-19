"""
Tests for restocking API endpoints.
"""
from datetime import datetime, timedelta

import pytest

import main


@pytest.fixture(autouse=True)
def reset_restocking_orders():
    """Reset the in-memory restocking orders between tests."""
    main.restocking_orders.clear()
    yield
    main.restocking_orders.clear()


ALL_SKUS_RANKED = [
    "FLT-405", "WDG-001", "GSK-203", "BRG-102", "PSU-501", "SNR-420", "CTL-330", "VLV-506",
]


def recommend(client, budget):
    response = client.get(f"/api/restocking/recommendations?budget={budget}")
    assert response.status_code == 200
    return response.json()


def place(client, budget, items):
    return client.post("/api/restocking/orders", json={"budget": budget, "items": items})


class TestRestockingRecommendations:
    """Test suite for the recommendations endpoint."""

    def test_forecast_data_has_cost_and_lead_time(self, client):
        """Every forecast carries unit_cost and lead_time_days."""
        data = client.get("/api/demand").json()
        assert len(data) == 9
        for f in data:
            assert isinstance(f["unit_cost"], (int, float))
            assert f["unit_cost"] > 0
            assert isinstance(f["lead_time_days"], int)
            assert f["lead_time_days"] > 0
        psu = next(f for f in data if f["item_sku"] == "PSU-501")
        assert psu["unit_cost"] == 18.99

    def test_huge_budget_returns_everything_in_ranked_order(self, client):
        """A huge budget buys full gaps for every item, ranked by priority."""
        data = recommend(client, 1000000)
        assert [i["sku"] for i in data["items"]] == ALL_SKUS_RANKED
        qty = {i["sku"]: i["quantity"] for i in data["items"]}
        assert qty == {
            "FLT-405": 150, "WDG-001": 150, "GSK-203": 100, "BRG-102": 2,
            "PSU-501": 2, "SNR-420": 2, "CTL-330": 1, "VLV-506": 1,
        }
        assert data["total_cost"] == 5148.48
        assert data["remaining_budget"] == round(1000000 - 5148.48, 2)

    def test_decreasing_and_zero_gap_items_never_recommended(self, client):
        """MTR-304 (decreasing demand) is never recommended."""
        skus = [i["sku"] for i in recommend(client, 1000000)["items"]]
        assert "MTR-304" not in skus

    def test_increasing_trend_ranks_before_stable(self, client):
        """All increasing items come before any stable item."""
        trends = [i["trend"] for i in recommend(client, 1000000)["items"]]
        assert trends == ["increasing"] * 3 + ["stable"] * 5

    def test_zero_budget_returns_nothing(self, client):
        """A zero budget gives an empty list and no spend."""
        data = recommend(client, 0)
        assert data["items"] == []
        assert data["total_cost"] == 0
        assert data["remaining_budget"] == 0

    def test_small_budget_partial_quantity(self, client):
        """Budget 2000: FLT-405 in full, WDG-001 partial (55 units)."""
        data = recommend(client, 2000)
        assert [(i["sku"], i["quantity"]) for i in data["items"]] == [
            ("FLT-405", 150), ("WDG-001", 55),
        ]
        assert data["items"][0]["line_total"] == 1312.5
        assert data["items"][1]["line_total"] == 687.5
        assert data["total_cost"] == 2000
        assert data["remaining_budget"] == 0
        assert "partial" in data["items"][1]["reason"]

    def test_budget_keeps_checking_cheaper_items_after_partial(self, client):
        """Budget 4000: GSK-203 gets 54 units, leaving 2.50 that buys nothing."""
        data = recommend(client, 4000)
        assert [(i["sku"], i["quantity"]) for i in data["items"]] == [
            ("FLT-405", 150), ("WDG-001", 150), ("GSK-203", 54),
        ]
        assert data["total_cost"] == 3997.5
        assert data["remaining_budget"] == 2.5

    def test_cheaper_item_still_fits_after_skipped_expensive_one(self, client):
        """Budget 1315: FLT-405 in full leaves 2.50, which is below every unit cost."""
        data = recommend(client, 1315)
        assert [(i["sku"], i["quantity"]) for i in data["items"]] == [("FLT-405", 150)]
        assert data["remaining_budget"] == 2.5

    def test_total_plus_remaining_equals_budget(self, client):
        """Total cost and remaining budget always add up to the budget."""
        for budget in [0, 10, 500, 2000, 4000, 5148.48, 6000]:
            data = recommend(client, budget)
            assert abs(data["total_cost"] + data["remaining_budget"] - budget) < 0.01
            assert data["remaining_budget"] >= 0

    def test_all_items_fit_with_exact_budget(self, client):
        """Exactly 5148.48 buys everything with nothing left."""
        data = recommend(client, 5148.48)
        assert len(data["items"]) == 8
        assert data["remaining_budget"] == 0

    def test_recommendation_line_structure(self, client):
        """Each line has the documented fields and consistent totals."""
        data = recommend(client, 6000)
        first = data["items"][0]
        assert first["sku"] == "FLT-405"
        assert first["name"] == "Oil Filter Cartridge"
        assert first["unit_cost"] == 8.75
        assert first["lead_time_days"] == 5
        assert first["trend"] == "increasing"
        assert isinstance(first["reason"], str) and first["reason"]
        for item in data["items"]:
            assert abs(item["line_total"] - item["quantity"] * item["unit_cost"]) < 0.01

    def test_negative_budget_rejected(self, client):
        """Negative budgets fail validation."""
        assert client.get("/api/restocking/recommendations?budget=-1").status_code == 422

    def test_budget_above_upper_bound_rejected(self, client):
        """Budgets above 1,000,000 fail validation."""
        assert client.get("/api/restocking/recommendations?budget=1000001").status_code == 422

    def test_missing_budget_rejected(self, client):
        """Budget is required."""
        assert client.get("/api/restocking/recommendations").status_code == 422


class TestRestockingOrders:
    """Test suite for submitting and listing restocking orders."""

    def test_no_orders_initially(self, client):
        """The orders list starts empty."""
        response = client.get("/api/restocking/orders")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_order_success(self, client):
        """A valid order returns 201 with computed totals."""
        response = place(client, 2000, [
            {"sku": "FLT-405", "quantity": 150}, {"sku": "WDG-001", "quantity": 55},
        ])
        assert response.status_code == 201
        order = response.json()
        assert order["order_number"] == "RST-2025-0001"
        assert order["status"] == "Submitted"
        assert order["total_cost"] == 2000
        assert [i["line_total"] for i in order["items"]] == [1312.5, 687.5]

    def test_server_side_pricing_ignores_client_prices(self, client):
        """Client-supplied prices are ignored; forecast prices are used."""
        response = client.post("/api/restocking/orders", json={
            "budget": 100,
            "items": [{"sku": "FLT-405", "quantity": 4, "unit_cost": 0.01, "line_total": 0.04}],
        })
        assert response.status_code == 201
        item = response.json()["items"][0]
        assert item["unit_cost"] == 8.75
        assert item["line_total"] == 35.0
        assert response.json()["total_cost"] == 35.0

    def test_unknown_sku_rejected(self, client):
        """Unknown SKUs return 400 and store nothing."""
        response = place(client, 1000, [{"sku": "NOPE-999", "quantity": 1}])
        assert response.status_code == 400
        assert "NOPE-999" in response.json()["detail"]
        assert client.get("/api/restocking/orders").json() == []

    @pytest.mark.parametrize("quantity", [0, -5])
    def test_non_positive_quantity_rejected(self, client, quantity):
        """Zero or negative quantities return 400."""
        response = place(client, 1000, [{"sku": "FLT-405", "quantity": quantity}])
        assert response.status_code == 400

    def test_over_budget_rejected(self, client):
        """A total above the budget returns 400."""
        response = place(client, 34.99, [{"sku": "FLT-405", "quantity": 4}])
        assert response.status_code == 400
        assert "budget" in response.json()["detail"].lower()
        assert client.get("/api/restocking/orders").json() == []

    def test_exact_budget_accepted(self, client):
        """A total equal to the budget is allowed."""
        assert place(client, 35.0, [{"sku": "FLT-405", "quantity": 4}]).status_code == 201

    def test_empty_items_rejected(self, client):
        """An order with no items returns 400."""
        assert place(client, 1000, []).status_code == 400

    def test_duplicate_sku_rejected(self, client):
        """Repeated SKUs return 400."""
        response = place(client, 1000, [
            {"sku": "FLT-405", "quantity": 1}, {"sku": "FLT-405", "quantity": 2},
        ])
        assert response.status_code == 400

    def test_malformed_body_rejected(self, client):
        """Missing fields fail validation."""
        assert client.post("/api/restocking/orders", json={"items": []}).status_code == 422

    def test_negative_budget_rejected(self, client):
        """A negative budget returns 400."""
        response = place(client, -1, [{"sku": "FLT-405", "quantity": 1}])
        assert response.status_code == 400

    def test_lead_time_is_max_of_items_and_expected_delivery(self, client):
        """Lead time is the longest item lead time; delivery is submitted date plus that."""
        response = place(client, 1000, [
            {"sku": "FLT-405", "quantity": 1},   # 5 days
            {"sku": "CTL-330", "quantity": 1},   # 21 days
            {"sku": "WDG-001", "quantity": 1},   # 7 days
        ])
        assert response.status_code == 201
        order = response.json()
        assert order["lead_time_days"] == 21
        submitted = datetime.fromisoformat(order["submitted_date"])
        expected = (submitted + timedelta(days=21)).strftime("%Y-%m-%d")
        assert order["expected_delivery"] == expected
        assert abs((datetime.now() - submitted).total_seconds()) < 60

    def test_single_item_lead_time(self, client):
        """A single-item order uses that item's lead time."""
        order = place(client, 1000, [{"sku": "FLT-405", "quantity": 1}]).json()
        assert order["lead_time_days"] == 5
        submitted = datetime.fromisoformat(order["submitted_date"])
        assert order["expected_delivery"] == (submitted + timedelta(days=5)).strftime("%Y-%m-%d")

    def test_orders_listed_newest_first(self, client):
        """GET returns the most recent order first, with incrementing numbers."""
        place(client, 1000, [{"sku": "FLT-405", "quantity": 1}])
        place(client, 1000, [{"sku": "WDG-001", "quantity": 1}])
        place(client, 1000, [{"sku": "GSK-203", "quantity": 1}])
        orders = client.get("/api/restocking/orders").json()
        assert [o["order_number"] for o in orders] == [
            "RST-2025-0003", "RST-2025-0002", "RST-2025-0001",
        ]
        assert [o["items"][0]["sku"] for o in orders] == ["GSK-203", "WDG-001", "FLT-405"]

    def test_submitted_orders_not_in_regular_orders(self, client):
        """Restocking orders do not leak into /api/orders."""
        before = len(client.get("/api/orders").json())
        place(client, 1000, [{"sku": "FLT-405", "quantity": 1}])
        assert len(client.get("/api/orders").json()) == before
