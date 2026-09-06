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


def get_product_details(product_id: int):
    try:
        product = (
            Product.objects
            .select_related("collection")
            .prefetch_related("productimage_set")
            .get(pk=product_id)
        )
    except Product.DoesNotExist:
        return {"error": f"No product found with id {product_id}."}

    return {
        "id": product.id,
        "title": product.title,
        "description": product.description or "",
        "price": str(product.price),
        "inventory": product.inventory,
        "collection": product.collection.title,
        "images": [
            image.image.url for image in product.productimage_set.all()
        ],
    }