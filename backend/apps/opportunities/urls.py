from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OpportunityViewSet, DuplicateCandidateViewSet

router = DefaultRouter()
router.register(r'opportunities', OpportunityViewSet, basename='opportunity')
router.register(r'duplicates', DuplicateCandidateViewSet, basename='duplicate')

urlpatterns = [
    path('', include(router.urls)),
]
