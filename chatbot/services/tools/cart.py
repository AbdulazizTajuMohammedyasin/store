"""
NOTE: every function here takes `customer` as a plain argument rather
than being a bare @tool itself, and customer is never taken from an
LLM-controlled argument. ChatAgent binds these to the authenticated
request's own customer via closures (see agent.py), so the assistant
can never be asked to modify another customer's cart.
"""

from products.models import CartItem, Product


def get_cart_contents(customer):
    cart = customer.cart
    items = list(cart.cartitem_set.select_related("product").all())

    if not items:
        return "The cart is empty."

    return {
        "items": [
            {
                "product_id": item.product.id,
                "title": item.product.title,
                "quantity": item.quantity,
                "unit_price": str(item.product.price),
                "total_price": str(item.product.price * item.quantity),
            }
            for item in items
        ],
        "total_price": str(
            sum(item.product.price * item.quantity for item in items)
        ),
    }


def add_item_to_cart(customer, product_id: int, quantity: int = 1):
    if quantity < 1:
        return {"error": "Quantity must be at least 1."}

    try:
        product = Product.objects.get(pk=product_id)
    except Product.DoesNotExist:
        return {"error": f"No product found with id {product_id}."}

    cart_item, created = CartItem.objects.get_or_create(
        cart=customer.cart,
        product=product,
        defaults={"quantity": quantity},
    )

    if not created:
        cart_item.quantity += quantity
        cart_item.save()

    return {
        "product_id": product.id,
        "title": product.title,
        "quantity": cart_item.quantity,
    }


def update_cart_item_quantity(customer, product_id: int, quantity: int):
    if quantity < 1:
        return {
            "error": (
                "Quantity must be at least 1. "
                "Use remove_from_cart to remove an item instead."
            )
        }

    try:
        cart_item = CartItem.objects.get(
            cart=customer.cart, product_id=product_id
        )
    except CartItem.DoesNotExist:
        return {"error": "That product is not in the cart."}

    cart_item.quantity = quantity
    cart_item.save()

    return {"product_id": product_id, "quantity": cart_item.quantity}


def remove_item_from_cart(customer, product_id: int):
    deleted, _ = CartItem.objects.filter(
        cart=customer.cart, product_id=product_id
    ).delete()

    if not deleted:
        return {"error": "That product is not in the cart."}

    return {"message": f"Removed product {product_id} from the cart."}
