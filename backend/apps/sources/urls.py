from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SourceViewSet, SearchTermViewSet, RunViewSet

router = DefaultRouter()
router.register(r'sources', SourceViewSet, basename='source')
router.register(r'search-terms', SearchTermViewSet, basename='search-term')
router.register(r'runs', RunViewSet, basename='run')

urlpatterns = [
    path('', include(router.urls)),
]
