from rest_framework import serializers
from .models import Product, Collection

class ProductSerializer(serializers.ModelSerializer):
    collection = serializers.StringRelatedField()
    class Meta:
        model = Product
        fields = ['id','title','description', 'collection'] 
    
class CollectionSerializer(serializers.ModelSerializer):
    featured_product = serializers.StringRelatedField()
    class Meta:
        model = Collection
        fields = ['id','title','featured_product']