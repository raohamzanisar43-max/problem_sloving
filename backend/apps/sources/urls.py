from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import IgnoreKeywordsView, SourceViewSet, SearchTermViewSet, RunViewSet

router = DefaultRouter()
router.register(r'sources', SourceViewSet, basename='source')
router.register(r'search-terms', SearchTermViewSet, basename='search-term')
router.register(r'runs', RunViewSet, basename='run')

urlpatterns = [
    path('ignore-keywords/', IgnoreKeywordsView.as_view(), name='ignore-keywords'),
    path('', include(router.urls)),
]
