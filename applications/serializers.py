from rest_framework import serializers
from .models import Application, Notification

# --- THE APPLICATION TRANSLATOR ---
# Logic: This class maps the 'Application' database table to JSON.
# It is used when a student checks their dashboard or when a company 
# reviews a list of applicants.
class ApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = ['id', 'applicationDate', 'applicationStatus', 'matchingScore', 'offer']
        
        # DATA INTEGRITY RULE: Read-Only fields.
        # Logic: We must ensure that a student cannot manipulate their own data.
        # By making these read_only, the Frontend can see them, but if a student 
        # tries to send a different 'matchingScore' or 'status' in a POST request, 
        # Django will ignore it. These are managed strictly by the Backend logic.
        read_only_fields = ['applicationDate', 'applicationStatus', 'matchingScore']


# --- THE NOTIFICATION TRANSLATOR ---
# Logic: This handles the data for your 'Alert System'.
# It sends the messages to the frontend to populate the bell icon on the dashboard.
class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'message', 'created_at', 'is_read']