from rest_framework_nested import routers
from .views import ProductViewSet,CollectionViewSet, CartViewSet, CartItemViewSet, CustomerViewSet, OrderViewSet, ProductImageViewSet

router = routers.DefaultRouter()
router.register(r'products', ProductViewSet)
router.register(r'collections',CollectionViewSet)
router.register(r'carts',CartViewSet)
router.register(r'customers',CustomerViewSet)
router.register(r'orders',OrderViewSet, basename='orders')


cart_router = routers.NestedDefaultRouter(router,'carts', lookup='cart')
cart_router.register(r'items', CartItemViewSet, basename='cart-item')

product_router = routers.NestedDefaultRouter(router, 'products', lookup='product')
product_router.register(r'images', ProductImageViewSet, basename='product-image')

urlpatterns = router.urls + cart_router.urls + product_router.urls
