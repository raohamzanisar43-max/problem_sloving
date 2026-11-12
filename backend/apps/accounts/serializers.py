from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    # Lets the web Settings screen show the keyword editors only to users the
    # API will accept changes from (admin / manager role, or a superuser).
    can_manage_keywords = serializers.BooleanField(source='is_manager_role', read_only=True)

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'role', 'display_name', 'first_name', 'last_name',
            'can_manage_keywords',
        )
        read_only_fields = ('id', 'username', 'role', 'can_manage_keywords')
