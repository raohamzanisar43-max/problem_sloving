from django.urls import path

from .views import OperatingSettingsView, health

urlpatterns = [
    path('health/', health, name='health'),
    path('settings/', OperatingSettingsView.as_view(), name='operating-settings'),
]
