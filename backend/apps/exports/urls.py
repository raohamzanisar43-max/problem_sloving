from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    OpportunityCSVExportView,
    OutboxEventViewSet,
    SyncJobViewSet,
    SyncTargetViewSet,
)

router = DefaultRouter()
router.register(r'sync/jobs', SyncJobViewSet, basename='sync-job')
router.register(r'sync/targets', SyncTargetViewSet, basename='sync-target')
router.register(r'outbox', OutboxEventViewSet, basename='outbox-event')

urlpatterns = [
    path('exports/opportunities.csv', OpportunityCSVExportView.as_view(), name='export-csv'),
    path('', include(router.urls)),
]
