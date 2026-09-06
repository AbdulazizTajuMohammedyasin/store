from langchain.tools import tool

from .products import get_product_details, search_products


@tool
def product_search(query: str):
    """
    Search products available in the store.
    """

    products = search_products(query)

    if not products:
        return "No matching products found."

    return products


@tool
def product_details(product_id: int):
    """
    Get full details for a single product by id, including its
    description, price, inventory, collection, and image URLs.
    """

    return get_product_details(product_id)
