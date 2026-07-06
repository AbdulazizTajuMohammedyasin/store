from django.shortcuts import render
from django.db.models import ProtectedError
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.viewsets import ModelViewSet, GenericViewSet
from rest_framework.mixins import DestroyModelMixin, CreateModelMixin, RetrieveModelMixin, ListModelMixin, UpdateModelMixin
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser, IsAuthenticatedOrReadOnly
from .permissions import IsAdminOrReadOnly, IsReviewOwner
from rest_framework import status
from rest_framework.response import Response 
from rest_framework.filters import SearchFilter, OrderingFilter
from .serializers import ProductSerializer, ProductCreateSerializer, CollectionSerializer, CartSerializer, CartItemSerializer, AddCartItemSerializer, UpdateCartItemSerializer, CustomerSerializer, OrderSerializer, OrderCreateSerializer, OrderUpdateSerializer, ProductImageSerializer, ReviewSerializer
from .models import Product, Collection, Cart, CartItem, Customer, Order, ProductImage, Review


class ProductViewSet(ModelViewSet):
    queryset = Product.objects.prefetch_related('productimage_set').all()
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
        OrderingFilter,
    ]
    filterset_fields = ['collection']
    search_fields = ['title', 'description']
    ordering_fields = ['last_update', 'title']
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ProductCreateSerializer

        return ProductSerializer
    
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
    permission_classes=[IsAdminOrReadOnly]
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

class CustomerViewSet(ModelViewSet):
    
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes=[IsAdminUser]
    
    @action(detail=False, methods=['GET', 'PUT'], permission_classes=[IsAuthenticated])
    def me(self, request):
        customer = Customer.objects.get(user_id= request.user.id)
        if request.method == 'GET':
            serializer = CustomerSerializer(customer)
            return Response(serializer.data)
        else:
            serializer = CustomerSerializer(customer, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
            
            
class OrderViewSet(ModelViewSet):

    
    http_method_names = ['get','post', 'head', 'options', 'patch', 'delete']
    
    def get_permissions(self):
        if self.request.method in ['PATCH', 'DELETE']:
            return [IsAdminUser()] 
        else:
            return [IsAuthenticated()]
    
    def create(self, request, *args, **kwargs):
        serializer = OrderCreateSerializer(data=request.data, context={'user_id':self.request.user.id})
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        serializer = OrderSerializer(order)
        return Response(serializer.data)
        
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return OrderCreateSerializer
        elif self.request.method == 'PATCH':
            return OrderUpdateSerializer
        return OrderSerializer

    def get_queryset(self):
        if self.request.user.is_staff:
            return Order.objects.prefetch_related("orderitem_set__product")
        
        customer = Customer.objects.get(user_id=self.request.user.id)
        return Order.objects.prefetch_related("orderitem_set__product").filter(customer=customer)    
    
class ProductImageViewSet(ModelViewSet):
    serializer_class = ProductImageSerializer
    
    def get_queryset(self):
        return ProductImage.objects.filter(product_id=self.kwargs['product_pk'])
    
    def get_serializer_context(self):
        return {'product_id':self.kwargs['product_pk']}
    
class ReviewViewSet(ModelViewSet):
    serializer_class = ReviewSerializer
    def get_permissions(self):
        if self.action in ["update", "partial_update", "destroy"]:
            return [IsAuthenticated(), IsReviewOwner()]

        return [IsAuthenticatedOrReadOnly()]
        

    def get_queryset(self):
        return Review.objects.select_related(
        'customer',
        'customer__user').filter(
            product_id=self.kwargs["product_pk"]
        )
        
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["product"] = Product.objects.get(id=self.kwargs["product_pk"])
        context["customer"] = self.request.user.customer
        return context
    