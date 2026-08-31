from products.models import Product


def search_products(query: str, limit: int = 5):
    products = (
        Product.objects
        .filter(title__icontains=query)
        .select_related("collection")
        [:limit]
    )

    return [
        {
            "id": product.id,
            "title": product.title,
            "price": str(product.price),
            "inventory": product.inventory,
            "collection": product.collection.title,
        }
        for product in products
    ]