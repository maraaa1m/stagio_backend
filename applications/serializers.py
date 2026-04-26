from rest_framework import serializers
from .models import Application, Internship, Agreement, Certificate, Notification

class CertificateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Certificate
        fields = ['id', 'issueDate', 'pdfUrl']

class InternshipSerializer(serializers.ModelSerializer):
    certificate = CertificateSerializer(read_only=True)
    class Meta:
        model = Internship
        fields = ['id', 'startDate', 'endDate', 'topic', 'supervisorName', 'status', 'certificate']

class ApplicationSerializer(serializers.ModelSerializer):
    internship = InternshipSerializer(read_only=True)
    class Meta:
        model = Application
        fields = ['id', 'applicationDate', 'applicationStatus', 'matchingScore', 'offer', 'internship']
        read_only_fields = ['applicationDate', 'applicationStatus', 'matchingScore']

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'message', 'created_at', 'is_read']