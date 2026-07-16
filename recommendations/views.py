from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated

from .models import ProductRecommendation, UserRecommendation
from .serializers import ProductRecommendationSerializer, UserRecommendationSerializer
from .services.content_based import content_based
from .services.collaborative import collaborative_filtering

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
        
class UserRecommendationView(ListAPIView):
    serializer_class = UserRecommendationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        customer = self.request.user.customer

        recommendations_exist = (
            UserRecommendation.objects
            .filter(customer=customer)
            .exists()
        )

        if not recommendations_exist:
            collaborative_filtering()

        return (
            UserRecommendation.objects
            .filter(customer=customer)
            .select_related('product')
            .order_by('-score')
        )