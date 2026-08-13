from rest_framework import serializers
from .models import Product, Collection, Cart, CartItem, Customer, Order, OrderItem, ProductImage, Review, Address
from django.db import transaction

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image']
        
    def create(self, validated_data):
        return ProductImage.objects.create(product_id=self.context['product_id'], **validated_data)

class ProductSerializer(serializers.ModelSerializer):
    collection = serializers.StringRelatedField()
    images = ProductImageSerializer(many=True, source='productimage_set', read_only=True )
    class Meta:
        model = Product
        fields = ['id','title','description', 'price', 'collection','images'] 
    
class ProductAdminSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, source='productimage_set', read_only=True)
 
    class Meta:
        model = Product
        fields = ['id', 'title', 'description', 'price', 'inventory', 'collection', 'images']

class ProductCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            'id',
            'title',
            'description',
            'inventory',
            'price',
            'collection'
        ]
        
class FeaturedProductSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "title",
            "image"
        ]

    def get_image(self, product):
        image = product.productimage_set.first()

        if image:
            request = self.context.get("request")
            return request.build_absolute_uri(image.image.url)

        return None   

class CollectionSerializer(serializers.ModelSerializer):
    featured_product = FeaturedProductSerializer()
    class Meta:
        model = Collection
        fields = ['id','title','featured_product']
        
class CollectionAdminSerializer(serializers.ModelSerializer):
    products_count = serializers.IntegerField(read_only=True)

    featured_product_details = FeaturedProductSerializer(
        source="featured_product",
        read_only=True
    )

    class Meta:
        model = Collection
        fields = [
            "id",
            "title",
            "featured_product",
            "featured_product_details",
            "products_count",
        ]        
    
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
        customer = Customer.objects.get(
                        user_id=self.context['user_id']
                    )
        cart = customer.cart 
        
        product_id = self.validated_data['product_id']
        quantity = self.validated_data['quantity']

        try:
            cart_item = CartItem.objects.get(cart=cart,product_id=product_id)
            cart_item.quantity += quantity
            cart_item.save()
            self.instance = cart_item
        except CartItem.DoesNotExist:
            cart_item = CartItem.objects.create(cart=cart, **self.validated_data)
            self.instance = cart_item

        return self.instance
    
class UpdateCartItemSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = CartItem
        fields = ['quantity']
        
class CustomerSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')
    email = serializers.EmailField(source='user.email')
    membership = serializers.CharField(read_only=True)
    profile_image = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = Customer
        fields = [
            'id', 'first_name', 'last_name', 'email',
            'phone', 'birth_date', 'membership', 'profile_image',
        ]

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if instance.profile_image:
            request = self.context.get('request')
            rep['profile_image'] = (
                request.build_absolute_uri(instance.profile_image.url)
                if request else instance.profile_image.url
            )
        else:
            rep['profile_image'] = None
        return rep

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        user = instance.user
        user.first_name = user_data.get('first_name', user.first_name)
        user.last_name = user_data.get('last_name', user.last_name)
        user.email = user_data.get('email', user.email)
        user.save()

        instance.phone = validated_data.get('phone', instance.phone)
        instance.birth_date = validated_data.get('birth_date', instance.birth_date)
        instance.profile_image = validated_data.get('profile_image', instance.profile_image)
        instance.save()

        return instance
    
class CustomerAdminSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(
        source='user.first_name',
        read_only=True
    )
    last_name = serializers.CharField(
        source='user.last_name',
        read_only=True
    )
    email = serializers.EmailField(
        source='user.email',
        read_only=True
    )

    class Meta:
        model = Customer
        fields = [
            'id',
            'first_name',
            'last_name',
            'email',
            'phone',
            'birth_date',
            'membership',
        ]
        read_only_fields = [
            'id',
            'phone',
            'birth_date',
        ]
         
class OrderItemSerializer(serializers.ModelSerializer):
    
    product = ProductSerializer1()
    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'quantity', 'unit_price']
         
class OrderSerializer(serializers.ModelSerializer):
    
    items = OrderItemSerializer(many=True, source='orderitem_set', read_only=True)
    class Meta:
        model = Order
        fields = ['id', 'placed_at', 'payment_status', 'customer', 'items']
        
class OrderCreateSerializer(serializers.Serializer):
    
    
    def save(self, **kwargs):
        customer = Customer.objects.get(
                    user_id=self.context['user_id']
                )
        cart = customer.cart
        
        if not CartItem.objects.filter(cart=cart).exists():
            raise serializers.ValidationError(
                "Cart is empty."
            )
        
        with transaction.atomic():
            order = Order.objects.create(customer=customer)
            cart_items = CartItem.objects.select_related('product').select_for_update().filter(cart = cart)
            
            #check the inventory
            for item in cart_items:
                if item.product.inventory < item.quantity:
                    raise serializers.ValidationError(
                        f"{item.product.title} does not have enough stock."
                    )

            # Deduct inventory
            for item in cart_items:
                item.product.inventory -= item.quantity
                item.product.save()
            
            
            order_items = [
                OrderItem(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    unit_price=item.product.price
                )
                for item in cart_items
            ]
            
            OrderItem.objects.bulk_create(order_items)
            CartItem.objects.filter(cart=cart).delete()
            
            return order 
       
class OrderUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['payment_status']
        
class ReviewSerializer(serializers.ModelSerializer):
    
    reviewed_by = serializers.CharField(
        source='customer.user.username',
        read_only=True
    )
    
    class Meta:
        model = Review
        fields = ["id","rating","comment","created_at","reviewed_by"]
        read_only_fields = ["created_at"]
    
    def get_customer(self):
        return self.context["customer"]

    def get_product(self):
        return self.context["product"]
        
    
    def validate(self, attrs):
        customer = self.get_customer()
        product = self.get_product()
        
        if self.context["request"].method == "POST" and Review.objects.filter(
            product=product,
            customer=customer
        ).exists():
            raise serializers.ValidationError({
            "detail": "You have already reviewed this product. Update the existing review instead."
            })

        return attrs

    def create(self, validated_data):
        customer = self.get_customer()

        product = self.get_product()

        return Review.objects.create(
            product=product,
            customer=customer,
            **validated_data
        )

class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ['id', 'street', 'city']