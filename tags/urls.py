from rest_framework_nested import routers
from .views import ProductTagViewSet
from products.views import ProductViewSet

router = routers.DefaultRouter()
router.register(r'products', ProductViewSet)

products_router = routers.NestedDefaultRouter(router,'products',lookup='product')

products_router.register('tags',ProductTagViewSet,basename='product-tags')

urlpatterns = router.urls + products_router.urls
