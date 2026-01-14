from django.shortcuts import render
from django.db.models import ProtectedError
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.viewsets import ModelViewSet, GenericViewSet
from rest_framework.mixins import DestroyModelMixin, CreateModelMixin, RetrieveModelMixin, ListModelMixin
from rest_framework import status
from rest_framework.response import Response 
from rest_framework.filters import SearchFilter, OrderingFilter
from .serializers import ProductSerializer, CollectionSerializer, CartSerializer, CartItemSerializer, AddCartItemSerializer, UpdateCartItemSerializer
from .models import Product, Collection, Cart, CartItem


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

class CartViewSet(ListModelMixin, RetrieveModelMixin, CreateModelMixin, DestroyModelMixin,GenericViewSet):
    queryset = Cart.objects.prefetch_related('cartitem_set__product')
    serializer_class = CartSerializer

class CartItemViewSet(ModelViewSet):
    
    http_method_names = ['get', 'post', 'patch', 'delete']
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return AddCartItemSerializer
        elif self.request.method == 'GET':
            return CartItemSerializer
        else :
            return UpdateCartItemSerializer
    
    def get_serializer_context(self):
        return {'cart_id':self.kwargs['cart_pk']}
        
    def get_queryset(self):
        return CartItem.objects.filter(cart_id=self.kwargs['cart_pk']).select_related('product')





