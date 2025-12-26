from django.shortcuts import render
from django.db.models import ProtectedError
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.viewsets import ModelViewSet
from rest_framework import status
from rest_framework.response import Response 
from rest_framework.filters import SearchFilter, OrderingFilter
from .serializers import ProductSerializer, CollectionSerializer
from .models import Product, Collection


class ProductViewSet(ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
        OrderingFilter,
    ]
    filterset_fields = ['collection']
    search_fields = ['title', 'description']
    ordering_fields = ['last_update', 'title']

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {
                    "error": "This product has been ordered and cannot be deleted."
                },
                status=status.HTTP_400_BAD_REQUEST
        )

class CollectionViewSet(ModelViewSet):
    queryset = Collection.objects.all()
    serializer_class = CollectionSerializer
    filter_backends = [
        SearchFilter,
        OrderingFilter,
    ]
    search_fields = ['title']
    ordering_fields = ['title']

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {
                    "error": "This collection has products inside it."
                },
                status=status.HTTP_400_BAD_REQUEST
        )






