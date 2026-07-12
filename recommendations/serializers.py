from rest_framework import serializers
from products.serializers import ProductSerializer
from recommendations.models import ProductRecommendation


class ProductRecommendationSerializer(serializers.ModelSerializer):
    product = ProductSerializer(
        source='recommended_product',
        read_only=True
    )

    class Meta:
        model = ProductRecommendation
        fields = ['product', 'score']