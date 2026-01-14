from rest_framework import serializers
from .models import Product, Collection, Cart, CartItem

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
    
class ProductSerializer1(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'title','price']
    
class CartItemSerializer(serializers.ModelSerializer):
    total_price = serializers.SerializerMethodField()
    product = ProductSerializer1()
    class Meta:
        model = CartItem
        fields = ['id','product','quantity','total_price']
    def get_total_price(self, cart_item):
        return cart_item.product.price * cart_item.quantity
    
class CartSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    cartitem_set = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()
    class Meta:
        model = Cart
        fields = ['id','cartitem_set','total_price']
    def get_total_price(self, cart):
        return sum(
            item.product.price * item.quantity
            for item in cart.cartitem_set.all()
        )
    
class AddCartItemSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField()
    class Meta:
        model = CartItem
        fields = ['id','product_id','quantity']

    def validate_product_id(self, value):
        if not Product.objects.filter(pk=value).exists():
            raise serializers.ValidationError('No product with the given ID was found.')
        return value   

    def save(self, **kwargs):
        cart_id = self.context['cart_id']
        product_id = self.validated_data['product_id']
        quantity = self.validated_data['quantity']

        try:
            cart_item = CartItem.objects.get(cart_id=cart_id,product_id=product_id)
            cart_item.quantity += quantity
            cart_item.save()
            self.instance = cart_item
        except CartItem.DoesNotExist:
            cart_item = CartItem.objects.create(cart_id=cart_id, **self.validated_data)
            self.instance = cart_item

        return self.instance
    
class UpdateCartItemSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = CartItem
        fields = ['quantity']