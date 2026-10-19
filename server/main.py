import math
import re
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from pydantic import BaseModel, Field
from mock_data import inventory_items, orders, demand_forecasts, backlog_items, spending_summary, monthly_spending, category_spending, recent_transactions, purchase_orders

app = FastAPI(title="Factory Inventory Management System")

# Quarter mapping for date filtering
QUARTER_MAP = {
    'Q1-2025': ['2025-01', '2025-02', '2025-03'],
    'Q2-2025': ['2025-04', '2025-05', '2025-06'],
    'Q3-2025': ['2025-07', '2025-08', '2025-09'],
    'Q4-2025': ['2025-10', '2025-11', '2025-12']
}

MONTH_PATTERN = re.compile(r'^\d{4}-\d{2}$')

def filter_by_month(items: list, month: Optional[str]) -> list:
    """Filter items by month (YYYY-MM) or quarter (e.g. Q1-2025) based on order_date field"""
    if not month or month.lower() == 'all':
        return items

    if MONTH_PATTERN.match(month):
        return [item for item in items if item.get('order_date', '').startswith(month)]

    quarter = month.upper()
    if quarter in QUARTER_MAP:
        months = tuple(QUARTER_MAP[quarter])
        return [item for item in items if item.get('order_date', '').startswith(months)]

    raise HTTPException(
        status_code=400,
        detail=f"Invalid month '{month}'. Use 'all', YYYY-MM, or a quarter such as {', '.join(QUARTER_MAP)}"
    )

def apply_filters(items: list, warehouse: Optional[str] = None, category: Optional[str] = None,
                 status: Optional[str] = None) -> list:
    """Apply common filters to a list of items"""
    filtered = items

    if warehouse and warehouse != 'all':
        filtered = [item for item in filtered if item.get('warehouse') == warehouse]

    if category and category != 'all':
        filtered = [item for item in filtered if item.get('category', '').lower() == category.lower()]

    if status and status != 'all':
        filtered = [item for item in filtered if item.get('status', '').lower() == status.lower()]

    return filtered

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data models
class InventoryItem(BaseModel):
    id: str
    sku: str
    name: str
    category: str
    warehouse: str
    quantity_on_hand: int
    reorder_point: int
    unit_cost: float
    location: str
    last_updated: str

class Order(BaseModel):
    id: str
    order_number: str
    customer: str
    items: List[dict]
    status: str
    order_date: str
    expected_delivery: str
    total_value: float
    actual_delivery: Optional[str] = None
    warehouse: Optional[str] = None
    category: Optional[str] = None

class DemandForecast(BaseModel):
    id: str
    item_sku: str
    item_name: str
    current_demand: int
    forecasted_demand: int
    trend: str
    period: str
    unit_cost: float
    lead_time_days: int

class BacklogItem(BaseModel):
    id: str
    order_id: str
    item_sku: str
    item_name: str
    quantity_needed: int
    quantity_available: int
    days_delayed: int
    priority: str
    has_purchase_order: Optional[bool] = False
    purchase_order_id: Optional[str] = None

class PurchaseOrder(BaseModel):
    id: str
    backlog_item_id: str
    supplier_name: str
    quantity: int
    unit_cost: float
    expected_delivery_date: str
    status: str
    created_date: str
    notes: Optional[str] = None

class CreatePurchaseOrderRequest(BaseModel):
    backlog_item_id: str
    supplier_name: str
    quantity: int = Field(gt=0)
    unit_cost: float = Field(gt=0)
    expected_delivery_date: str
    notes: Optional[str] = None

# API endpoints
@app.get("/")
def root():
    return {"message": "Factory Inventory Management System API", "version": "1.0.0"}

@app.get("/api/inventory", response_model=List[InventoryItem])
def get_inventory(
    warehouse: Optional[str] = None,
    category: Optional[str] = None
):
    """Get all inventory items with optional filtering"""
    return apply_filters(inventory_items, warehouse, category)

@app.get("/api/inventory/{item_id}", response_model=InventoryItem)
def get_inventory_item(item_id: str):
    """Get a specific inventory item"""
    item = next((item for item in inventory_items if item["id"] == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@app.get("/api/orders", response_model=List[Order])
def get_orders(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None
):
    """Get all orders with optional filtering"""
    filtered_orders = apply_filters(orders, warehouse, category, status)
    filtered_orders = filter_by_month(filtered_orders, month)
    return filtered_orders

@app.get("/api/orders/{order_id}", response_model=Order)
def get_order(order_id: str):
    """Get a specific order"""
    order = next((order for order in orders if order["id"] == order_id), None)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@app.get("/api/demand", response_model=List[DemandForecast])
def get_demand_forecasts():
    """Get demand forecasts"""
    return demand_forecasts

@app.get("/api/backlog", response_model=List[BacklogItem])
def get_backlog():
    """Get backlog items with purchase order status"""
    result = []
    for item in backlog_items:
        item_dict = dict(item)
        po = latest_purchase_order(item["id"])
        item_dict["has_purchase_order"] = po is not None
        item_dict["purchase_order_id"] = po["id"] if po else None
        result.append(item_dict)
    return result

def latest_purchase_order(backlog_item_id: str) -> Optional[dict]:
    """Most recently created purchase order for a backlog item, or None"""
    matches = [po for po in purchase_orders if po["backlog_item_id"] == backlog_item_id]
    return matches[-1] if matches else None

@app.post("/api/purchase-orders", response_model=PurchaseOrder, status_code=201)
def create_purchase_order(request: CreatePurchaseOrderRequest):
    """Create a purchase order for a backlog item"""
    if not any(item["id"] == request.backlog_item_id for item in backlog_items):
        raise HTTPException(status_code=404, detail=f"Backlog item {request.backlog_item_id} not found")

    next_id = max((int(po["id"]) for po in purchase_orders if po["id"].isdigit()), default=0) + 1
    po = {
        **request.model_dump(),
        "id": str(next_id),
        "status": "Pending",
        "created_date": datetime.now().isoformat(timespec="seconds"),
    }
    purchase_orders.append(po)
    return po

@app.get("/api/purchase-orders/{backlog_item_id}", response_model=PurchaseOrder)
def get_purchase_order(backlog_item_id: str):
    """Get the most recent purchase order for a backlog item"""
    po = latest_purchase_order(backlog_item_id)
    if po is None:
        raise HTTPException(status_code=404, detail=f"Purchase order for backlog item {backlog_item_id} not found")
    return po

# ---- Restocking ----
MAX_RESTOCK_BUDGET = 1_000_000.0

class RestockRecommendation(BaseModel):
    sku: str
    name: str
    quantity: int
    unit_cost: float
    line_total: float
    lead_time_days: int
    trend: str
    reason: str

class RestockRecommendationsResponse(BaseModel):
    budget: float
    items: List[RestockRecommendation]
    total_cost: float
    remaining_budget: float

class RestockOrderItemRequest(BaseModel):
    sku: str
    quantity: int

class CreateRestockOrderRequest(BaseModel):
    budget: float
    items: List[RestockOrderItemRequest]

class RestockOrderItem(BaseModel):
    sku: str
    name: str
    quantity: int
    unit_cost: float
    line_total: float
    lead_time_days: int

class RestockOrder(BaseModel):
    id: str
    order_number: str
    items: List[RestockOrderItem]
    total_cost: float
    status: str
    submitted_date: str
    lead_time_days: int
    expected_delivery: str

# In-memory store; resets on restart
restocking_orders: List[dict] = []

def build_recommendations(budget: float) -> dict:
    candidates = []
    for f in demand_forecasts:
        gap = max(0, f["forecasted_demand"] - f["current_demand"])
        if gap > 0:
            candidates.append((f, gap))
    candidates.sort(key=lambda c: (0 if c[0]["trend"] == "increasing" else 1, -c[1], c[0]["item_sku"]))

    remaining = round(budget, 2)
    items = []
    for f, gap in candidates:
        cost = f["unit_cost"]
        if round(gap * cost, 2) <= remaining:
            qty = gap
        else:
            qty = min(gap, math.floor(round(remaining / cost, 6)))
        if qty < 1:
            continue
        line_total = round(qty * cost, 2)
        remaining = round(remaining - line_total, 2)
        reason = f"Demand {f['trend']}: {f['current_demand']} to {f['forecasted_demand']} (gap {gap} units)"
        if qty < gap:
            reason += f"; partial fill, {qty} of {gap} units fit the budget"
        items.append({
            "sku": f["item_sku"], "name": f["item_name"], "quantity": qty,
            "unit_cost": cost, "line_total": line_total,
            "lead_time_days": f["lead_time_days"], "trend": f["trend"], "reason": reason,
        })
    total = round(sum(i["line_total"] for i in items), 2)
    return {"budget": budget, "items": items, "total_cost": total, "remaining_budget": round(budget - total, 2)}

@app.get("/api/restocking/recommendations", response_model=RestockRecommendationsResponse)
def get_restocking_recommendations(budget: float = Query(..., ge=0, le=MAX_RESTOCK_BUDGET)):
    """Recommend items to restock within a budget"""
    return build_recommendations(budget)

@app.post("/api/restocking/orders", response_model=RestockOrder, status_code=201)
def create_restocking_order(request: CreateRestockOrderRequest):
    """Submit a restocking order; prices are recomputed server-side"""
    if request.budget < 0 or request.budget > MAX_RESTOCK_BUDGET:
        raise HTTPException(status_code=400, detail="Budget out of range")
    if not request.items:
        raise HTTPException(status_code=400, detail="Order must contain at least one item")

    forecasts = {f["item_sku"]: f for f in demand_forecasts}
    seen = set()
    lines = []
    for req in request.items:
        if req.sku in seen:
            raise HTTPException(status_code=400, detail=f"Duplicate SKU: {req.sku}")
        seen.add(req.sku)
        forecast = forecasts.get(req.sku)
        if not forecast:
            raise HTTPException(status_code=400, detail=f"Unknown SKU: {req.sku}")
        if req.quantity <= 0:
            raise HTTPException(status_code=400, detail=f"Quantity must be positive for {req.sku}")
        lines.append({
            "sku": req.sku, "name": forecast["item_name"], "quantity": req.quantity,
            "unit_cost": forecast["unit_cost"],
            "line_total": round(req.quantity * forecast["unit_cost"], 2),
            "lead_time_days": forecast["lead_time_days"],
        })

    total = round(sum(l["line_total"] for l in lines), 2)
    if total > request.budget:
        raise HTTPException(status_code=400, detail="Order total exceeds budget")

    now = datetime.now()
    lead = max(l["lead_time_days"] for l in lines)
    seq = len(restocking_orders) + 1
    order = {
        "id": f"rst-{seq}",
        "order_number": f"RST-2025-{seq:04d}",
        "items": lines,
        "total_cost": total,
        "status": "Submitted",
        "submitted_date": now.isoformat(timespec="seconds"),
        "lead_time_days": lead,
        "expected_delivery": (now + timedelta(days=lead)).strftime("%Y-%m-%d"),
    }
    restocking_orders.append(order)
    return order

@app.get("/api/restocking/orders", response_model=List[RestockOrder])
def get_restocking_orders():
    """Get submitted restocking orders, newest first"""
    return list(reversed(restocking_orders))

@app.get("/api/dashboard/summary")
def get_dashboard_summary(
    warehouse: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    month: Optional[str] = None
):
    """Get summary statistics for dashboard with optional filtering"""
    # Filter inventory
    filtered_inventory = apply_filters(inventory_items, warehouse, category)

    # Filter orders
    filtered_orders = apply_filters(orders, warehouse, category, status)
    filtered_orders = filter_by_month(filtered_orders, month)

    total_inventory_value = sum(item["quantity_on_hand"] * item["unit_cost"] for item in filtered_inventory)
    low_stock_items = len([item for item in filtered_inventory if item["quantity_on_hand"] <= item["reorder_point"]])
    pending_orders = len([order for order in filtered_orders if order["status"] in ["Processing", "Backordered"]])
    total_backlog_items = len(backlog_items)

    return {
        "total_inventory_value": round(total_inventory_value, 2),
        "low_stock_items": low_stock_items,
        "pending_orders": pending_orders,
        "total_backlog_items": total_backlog_items,
        "total_orders_value": sum(order["total_value"] for order in filtered_orders)
    }

@app.get("/api/spending/summary")
def get_spending_summary():
    """Get spending summary statistics"""
    return spending_summary

@app.get("/api/spending/monthly")
def get_monthly_spending():
    """Get monthly spending breakdown"""
    return monthly_spending

@app.get("/api/spending/categories")
def get_category_spending():
    """Get spending by category"""
    return category_spending

@app.get("/api/spending/transactions")
def get_recent_transactions():
    """Get recent transactions"""
    return recent_transactions

@app.get("/api/reports/quarterly")
def get_quarterly_reports():
    """Get quarterly performance reports"""
    # Calculate quarterly statistics from orders
    quarters = {}

    for order in orders:
        order_date = order.get('order_date', '')
        # Determine quarter
        if '2025-01' in order_date or '2025-02' in order_date or '2025-03' in order_date:
            quarter = 'Q1-2025'
        elif '2025-04' in order_date or '2025-05' in order_date or '2025-06' in order_date:
            quarter = 'Q2-2025'
        elif '2025-07' in order_date or '2025-08' in order_date or '2025-09' in order_date:
            quarter = 'Q3-2025'
        elif '2025-10' in order_date or '2025-11' in order_date or '2025-12' in order_date:
            quarter = 'Q4-2025'
        else:
            continue

        if quarter not in quarters:
            quarters[quarter] = {
                'quarter': quarter,
                'total_orders': 0,
                'total_revenue': 0,
                'delivered_orders': 0,
                'avg_order_value': 0
            }

        quarters[quarter]['total_orders'] += 1
        quarters[quarter]['total_revenue'] += order.get('total_value', 0)
        if order.get('status') == 'Delivered':
            quarters[quarter]['delivered_orders'] += 1

    # Calculate averages and fulfillment rate
    result = []
    for q, data in quarters.items():
        if data['total_orders'] > 0:
            data['avg_order_value'] = round(data['total_revenue'] / data['total_orders'], 2)
            data['fulfillment_rate'] = round((data['delivered_orders'] / data['total_orders']) * 100, 1)
        result.append(data)

    # Sort by quarter
    result.sort(key=lambda x: x['quarter'])
    return result

@app.get("/api/reports/monthly-trends")
def get_monthly_trends():
    """Get month-over-month trends"""
    months = {}

    for order in orders:
        order_date = order.get('order_date', '')
        if not order_date:
            continue

        # Extract month (format: YYYY-MM-DD)
        month = order_date[:7]  # Gets YYYY-MM

        if month not in months:
            months[month] = {
                'month': month,
                'order_count': 0,
                'revenue': 0,
                'delivered_count': 0
            }

        months[month]['order_count'] += 1
        months[month]['revenue'] += order.get('total_value', 0)
        if order.get('status') == 'Delivered':
            months[month]['delivered_count'] += 1

    # Convert to list and sort
    result = list(months.values())
    result.sort(key=lambda x: x['month'])
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
