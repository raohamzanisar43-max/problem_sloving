"""
URL configuration for Novu Opportunity Radar.
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/v1/', include('apps.core.urls')),
    path('api/v1/', include('apps.accounts.urls')),
    path('api/v1/', include('apps.sources.urls')),
    path('api/v1/', include('apps.observations.urls')),
    path('api/v1/', include('apps.opportunities.urls')),
    path('api/v1/', include('apps.contacts.urls')),
    path('api/v1/', include('apps.exports.urls')),
]
