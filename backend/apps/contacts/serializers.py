from rest_framework import serializers

from .models import Contact


class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = (
            'id', 'opportunity', 'company_name', 'company_domain', 'name',
            'designation', 'email', 'phone', 'evidence_url', 'verification',
            'is_primary', 'suppressed', 'fetched_at', 'created_at',
        )
        read_only_fields = ('id', 'created_at')
