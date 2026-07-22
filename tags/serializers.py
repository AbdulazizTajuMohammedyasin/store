from rest_framework import serializers
from .models import Tag, TaggedItem
from django.contrib.contenttypes.models import ContentType
from products.models import Product

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'label']

class AddTagSerializer(serializers.Serializer):
    label = serializers.CharField(max_length=50)

    def save(self, **kwargs):
        product = self.context['product']

        tag, _ = Tag.objects.get_or_create(
            label=self.validated_data['label']
        )

        product_type = ContentType.objects.get_for_model(Product)

        TaggedItem.objects.get_or_create(
            tag=tag,
            content_type=product_type,
            object_id=product.id
        )

        return tag