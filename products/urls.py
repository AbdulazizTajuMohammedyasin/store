from rest_framework_nested import routers
from .views import ProductViewSet,CollectionViewSet, CartViewSet, CartItemViewSet, CustomerViewSet, OrderViewSet, ProductImageViewSet, ReviewViewSet, AddressViewSet, AdminCollectionViewSet, ReviewSummaryViewSet

router = routers.DefaultRouter()
router.register(r'products', ProductViewSet)
router.register(r'collections',CollectionViewSet)
router.register(r'cart',CartViewSet)
router.register(r'cart-items', CartItemViewSet, basename='cart-item')
router.register(r'customers',CustomerViewSet)
router.register(r'orders',OrderViewSet, basename='orders')
router.register(r'addresses', AddressViewSet, basename='addresses')
router.register(r'admin-collections', AdminCollectionViewSet, basename='admin-collections')


product_router = routers.NestedDefaultRouter(router, 'products', lookup='product')
product_router.register(r'images', ProductImageViewSet, basename='product-image')
product_router.register(r'reviews', ReviewViewSet, basename='product-review')
product_router.register(r'summary', ReviewSummaryViewSet, basename='product-summary')

urlpatterns = router.urls  + product_router.urls
