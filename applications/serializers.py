from rest_framework import serializers
from .models import Application


class ApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = [
            'id',
            'applicationDate',
            'applicationStatus',
            'matchingScore',
            'offer',
        ]
        read_only_fields = [
            'applicationDate',
            'applicationStatus',
            'matchingScore',
        ]