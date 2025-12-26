from rest_framework.routers import DefaultRouter
from .views import ProductViewSet,CollectionViewSet

router = DefaultRouter()
router.register(r'products', ProductViewSet)
router.register(r'collections',CollectionViewSet)
urlpatterns = router.urls
