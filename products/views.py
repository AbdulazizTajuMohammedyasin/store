from django.shortcuts import render
from django.db.models import ProtectedError
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.viewsets import ModelViewSet, GenericViewSet
from rest_framework.mixins import DestroyModelMixin, CreateModelMixin, RetrieveModelMixin, ListModelMixin, UpdateModelMixin
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser, IsAuthenticatedOrReadOnly
from rest_framework.exceptions import ValidationError
from .permissions import IsAdminOrReadOnly, IsReviewOwner
from rest_framework import status
from rest_framework.response import Response 
from rest_framework.filters import SearchFilter, OrderingFilter
from .serializers import ProductSerializer, ProductCreateSerializer, CollectionSerializer, CartSerializer, CartItemSerializer, AddCartItemSerializer, UpdateCartItemSerializer, CustomerSerializer, OrderSerializer, OrderCreateSerializer, OrderUpdateSerializer, ProductImageSerializer, ReviewSerializer, CustomerAdminSerializer, AddressSerializer
from .models import Product, Collection, Cart, CartItem, Customer, Order, ProductImage, Review, Address
from .filters import ProductFilter
from .pagination import ProductPagination


class ProductViewSet(ModelViewSet):
    queryset = Product.objects.prefetch_related('productimage_set').all()
    permission_classes = [IsAdminOrReadOnly]
    pagination_class = ProductPagination
    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
        OrderingFilter,
    ]
    filterset_class = ProductFilter
    search_fields = ['title', 'description']
    ordering_fields = ['last_update', 'title', 'price']
    
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

class CartViewSet(ListModelMixin, RetrieveModelMixin, GenericViewSet):
    queryset = Cart.objects.prefetch_related('cartitem_set__product')
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Cart.objects.prefetch_related('cartitem_set__product').filter(customer__user=self.request.user)
    

class CartItemViewSet(ModelViewSet):
    
    http_method_names = ['get', 'post', 'patch', 'delete']
    permission_classes= [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return AddCartItemSerializer

        if self.action in ['list', 'retrieve']:
            return CartItemSerializer

        return UpdateCartItemSerializer
    
    def get_serializer_context(self):
        return {
                'user_id': self.request.user.id
                }
        
    def get_queryset(self):
        return CartItem.objects.filter(cart__customer__user=self.request.user).select_related('product')

class CustomerViewSet(ModelViewSet):
    
    queryset = Customer.objects.select_related('user').all()
    serializer_class = CustomerSerializer
    permission_classes=[IsAdminUser]
    
    def get_serializer_class(self):
        if self.action == 'me':
            return CustomerSerializer
        return CustomerAdminSerializer
    
    @action(detail=False, methods=['GET', 'PUT', 'PATCH'], permission_classes=[IsAuthenticated])
    def me(self, request):
        customer = Customer.objects.get(user_id= request.user.id)
        if request.method == 'GET':
            serializer = CustomerSerializer(customer, context={'request': request})
            return Response(serializer.data)
        else:
            serializer = CustomerSerializer(customer,data=request.data, partial=request.method == 'PATCH', context={'request': request})
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
        if self.request.user.is_authenticated:
            context["customer"] = self.request.user.customer
        return context
    
class AddressViewSet(ModelViewSet):
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(
            customer__user=self.request.user
        )

    def perform_create(self, serializer):
        customer = Customer.objects.get(
            user=self.request.user
        )

        if Address.objects.filter(customer=customer).exists():
            raise ValidationError(
                "Address already exists."
            )

        serializer.save(customer=customer)