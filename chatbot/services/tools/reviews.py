from django.conf import settings
from django.core.cache import cache
from django.db.models import Avg
from langchain.tools import tool

from products.models import Product, Review
from products.services import GeminiClient, GeminiServiceError, ReviewPromptBuilder

MAX_REVIEWS_FOR_SUMMARY = 200


def get_product_review_summary(product_id: int):
    if not Product.objects.filter(pk=product_id).exists():
        return {"error": f"No product found with id {product_id}."}

    reviews = Review.objects.filter(product_id=product_id)
    review_count = reviews.count()

    if review_count == 0:
        return {
            "review_count": 0,
            "average_rating": None,
            "summary": "This product has no reviews yet.",
        }

    average_rating = reviews.aggregate(avg=Avg("rating"))["avg"]

    # Reuse the same cache key/shape as the product-page review summary
    # endpoint, so the two features share one cached AI summary.
    cache_key = f"review_summary_{product_id}"
    cached = cache.get(cache_key)

    if cached:
        summary = cached["summary"]
    else:
        recent_reviews = list(
            reviews.order_by("-created_at")[:MAX_REVIEWS_FOR_SUMMARY]
        )
        prompt = ReviewPromptBuilder.build(recent_reviews)

        try:
            summary = GeminiClient().summarize(prompt)
        except GeminiServiceError:
            summary = "A review summary isn't available right now."
        else:
            cache.set(
                cache_key,
                {"summary": summary},
                timeout=settings.REVIEW_SUMMARY_CACHE_TTL,
            )

    return {
        "review_count": review_count,
        "average_rating": round(average_rating, 1),
        "summary": summary,
    }


@tool
def product_reviews(product_id: int):
    """
    Get the review summary for a product by id: number of reviews,
    average rating, and an AI-generated summary of customer sentiment.
    """

    return get_product_review_summary(product_id)
