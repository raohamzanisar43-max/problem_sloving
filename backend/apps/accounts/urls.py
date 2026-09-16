from django.urls import path
from .views import MeView, UserListView

urlpatterns = [
    path('me/', MeView.as_view(), name='me'),
    path('users/', UserListView.as_view(), name='user-list'),
]
