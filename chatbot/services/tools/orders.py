"""
NOTE: every function here takes `customer` as a plain argument rather
than being a bare @tool itself, and customer is never taken from an
LLM-controlled argument. ChatAgent binds these to the authenticated
request's own customer via closures (see agent.py). get_order_details
additionally filters by that customer, so an order_id belonging to
another customer simply looks like it doesn't exist.
"""

from products.models import Order

RESULT_LIMIT = 10


def list_orders_for_customer(customer, limit: int = RESULT_LIMIT):
    orders = (
        Order.objects
        .filter(customer=customer)
        .order_by("-placed_at")[:limit]
    )

    if not orders:
        return "No orders found."

    return [
        {
            "id": order.id,
            "placed_at": order.placed_at.isoformat(),
            "payment_status": order.get_payment_status_display(),
        }
        for order in orders
    ]


def get_order_details_for_customer(customer, order_id: int):
    try:
        order = (
            Order.objects
            .prefetch_related("orderitem_set__product")
            .get(pk=order_id, customer=customer)
        )
    except Order.DoesNotExist:
        return {"error": f"No order found with id {order_id}."}

    return {
        "id": order.id,
        "placed_at": order.placed_at.isoformat(),
        "payment_status": order.get_payment_status_display(),
        "items": [
            {
                "product_id": item.product.id,
                "title": item.product.title,
                "quantity": item.quantity,
                "unit_price": str(item.unit_price),
                "total_price": str(item.unit_price * item.quantity),
            }
            for item in order.orderitem_set.all()
        ],
    }
