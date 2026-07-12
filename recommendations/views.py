from rest_framework.generics import ListAPIView

from .models import ProductRecommendation
from .serializers import ProductRecommendationSerializer
from .services.content_based import content_based

class SimilarProductsView(ListAPIView):
    serializer_class = ProductRecommendationSerializer

    def get_queryset(self):
        product_id = self.kwargs['product_id']
        
        recommendations_exist = ProductRecommendation.objects.exists()

        if not recommendations_exist:
            content_based()

        return (
            ProductRecommendation.objects
            .filter(product_id=product_id)
            .select_related('recommended_product')
            .order_by('-score')
        )