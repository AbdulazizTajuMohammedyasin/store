from langchain.tools import tool

from products.models import Product
from recommendations.models import ProductRecommendation, UserRecommendation
from recommendations.services.collaborative import collaborative_filtering
from recommendations.services.content_based import content_based

RESULT_LIMIT = 5


def get_similar_products(product_id: int, limit: int = RESULT_LIMIT):
    if not Product.objects.filter(pk=product_id).exists():
        return {"error": f"No product found with id {product_id}."}

    if not ProductRecommendation.objects.exists():
        content_based()

    recommendations = (
        ProductRecommendation.objects
        .filter(product_id=product_id)
        .select_related("recommended_product")
        .order_by("-score")[:limit]
    )

    if not recommendations:
        return "No similar products found."

    return [
        {
            "id": rec.recommended_product.id,
            "title": rec.recommended_product.title,
            "price": str(rec.recommended_product.price),
        }
        for rec in recommendations
    ]


def get_recommended_products_for_customer(customer_id: int, limit: int = RESULT_LIMIT):
    """
    NOTE: customer_id is not exposed as an LLM-callable tool argument.
    ChatAgent binds this to the authenticated request's own customer via
    a closure (see agent.py) so the assistant can never be asked to look
    up another customer's recommendations.
    """
    if not UserRecommendation.objects.filter(customer_id=customer_id).exists():
        collaborative_filtering()

    recommendations = (
        UserRecommendation.objects
        .filter(customer_id=customer_id)
        .select_related("product")
        .order_by("-score")[:limit]
    )

    if not recommendations:
        return "No personalized recommendations are available yet."

    return [
        {
            "id": rec.product.id,
            "title": rec.product.title,
            "price": str(rec.product.price),
        }
        for rec in recommendations
    ]


@tool
def similar_products(product_id: int):
    """
    Get products similar to a given product by id, based on shared
    title/collection/description content.
    """

    return get_similar_products(product_id)
