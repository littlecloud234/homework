from rest_framework.routers import DefaultRouter

from .views import DocumentViewSet, IngestionJobViewSet

router = DefaultRouter()
router.register("documents", DocumentViewSet, basename="document")
router.register("ingestion-jobs", IngestionJobViewSet, basename="ingestion-job")

urlpatterns = router.urls
