from rest_framework_nested import routers
from .views import ProductViewSet,CollectionViewSet, CartViewSet, CartItemViewSet

router = routers.DefaultRouter()
router.register(r'products', ProductViewSet)
router.register(r'collections',CollectionViewSet)
router.register(r'carts',CartViewSet)

cart_router = routers.NestedDefaultRouter(router,'carts', lookup='cart')
cart_router.register(r'items', CartItemViewSet, basename='cart-item')

urlpatterns = router.urls + cart_router.urls 
