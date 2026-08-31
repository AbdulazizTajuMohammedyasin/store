from langchain.tools import tool

from .products import search_products


@tool
def product_search(query: str):
    """
    Search products available in the store.
    """

    products = search_products(query)

    if not products:
        return "No matching products found."

    return products
