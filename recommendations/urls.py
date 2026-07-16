from django.urls import path

from .views import SimilarProductsView, UserRecommendationView

urlpatterns = [
    path(
        'products/<int:product_id>/similar/',
        SimilarProductsView.as_view(),
        name='similar-products'
    ),
    path(
        'recommendations/',
        UserRecommendationView.as_view(),
        name='user-recommendations'
    ),
]