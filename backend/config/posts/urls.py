from rest_framework.routers import DefaultRouter
from django.urls import path
from .views import PostViewSet, community_counts

router = DefaultRouter()
router.register('', PostViewSet, basename='posts')

urlpatterns = router.urls + [
    path('community-counts/', community_counts, name='community-counts'),
]
