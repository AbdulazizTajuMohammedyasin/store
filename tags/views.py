from django.contrib.contenttypes.models import ContentType

from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import (
    ListModelMixin,
    CreateModelMixin,
    DestroyModelMixin
)

from products.models import Product
from .models import Tag, TaggedItem
from .serializers import TagSerializer, AddTagSerializer

class ProductTagViewSet(
    ListModelMixin,
    CreateModelMixin,
    DestroyModelMixin,
    GenericViewSet
):
    lookup_url_kwarg = 'tag_pk'

    def get_permissions(self):
        if self.action in ['create', 'destroy']:
            from rest_framework.permissions import IsAdminUser
            return [IsAdminUser()]
        return []

    def get_serializer_class(self):
        if self.action == 'create':
            return AddTagSerializer
        return TagSerializer

    def get_serializer_context(self):
        return {
            'product': Product.objects.get(
                pk=self.kwargs['product_pk']
            )
        }

    def get_queryset(self):
        product_id = self.kwargs['product_pk']

        product_type = ContentType.objects.get_for_model(Product)

        return Tag.objects.filter(
            taggeditem__content_type=product_type,
            taggeditem__object_id=product_id
        )

    def destroy(self, request, *args, **kwargs):
        product_id = self.kwargs['product_pk']
        tag_id = self.kwargs['tag_pk']

        product_type = ContentType.objects.get_for_model(Product)

        TaggedItem.objects.filter(
            content_type=product_type,
            object_id=product_id,
            tag_id=tag_id
        ).delete()

        return Response(status=status.HTTP_204_NO_CONTENT)