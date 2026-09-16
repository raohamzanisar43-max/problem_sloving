from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import User
from .serializers import UserSerializer


class MeView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class UserListView(generics.ListAPIView):
    """Sales managers and admins can list users for assignment dropdowns."""
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer
    queryset = User.objects.filter(is_active=True).order_by('display_name', 'username')
    ordering = ['display_name', 'username']

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_manager_role:
            # Executives only see themselves
            return qs.filter(pk=self.request.user.pk)
        return qs
