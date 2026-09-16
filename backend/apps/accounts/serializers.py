from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'role', 'display_name', 'first_name', 'last_name')
        read_only_fields = ('id', 'username', 'role')
