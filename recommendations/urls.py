from django.urls import path

from .views import SimilarProductsView

urlpatterns = [
    path(
        'products/<int:product_id>/similar/',
        SimilarProductsView.as_view(),
        name='similar-products'
    ),
]