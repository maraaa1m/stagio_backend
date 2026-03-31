from rest_framework import serializers
from .models import Application, Notification

class ApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = ['id', 'applicationDate', 'applicationStatus', 'matchingScore', 'offer']
        read_only_fields = ['applicationDate', 'applicationStatus', 'matchingScore']

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'message', 'created_at', 'is_read']