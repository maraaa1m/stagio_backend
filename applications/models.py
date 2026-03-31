from django.db import models
from accounts.models import User, Student, Admin
from offers.models import InternshipOffer

class Application(models.Model):
    PENDING = 'PENDING'
    ACCEPTED = 'ACCEPTED'
    REFUSED = 'REFUSED'
    VALIDATED = 'VALIDATED'

    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (ACCEPTED, 'Accepted'),
        (REFUSED, 'Refused'),
        (VALIDATED, 'Validated'),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='applications')
    offer = models.ForeignKey(InternshipOffer, on_delete=models.CASCADE, related_name='applications')
    applicationDate = models.DateField(auto_now_add=True)
    applicationStatus = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    matchingScore = models.FloatField(default=0.0)

    def __str__(self):
        return f"{self.student} -> {self.offer}"

class Internship(models.Model):
    application = models.OneToOneField(Application, on_delete=models.CASCADE, related_name='internship')
    startDate = models.DateField()
    endDate = models.DateField()
    topic = models.CharField(max_length=200)
    supervisorName = models.CharField(max_length=200)

    def __str__(self):
        return f"Internship: {self.application.student}"

class Agreement(models.Model):
    GENERATED = 'GENERATED'
    VALIDATED = 'VALIDATED'
    DOWNLOADED = 'DOWNLOADED'

    STATUS_CHOICES = [
        (GENERATED, 'Generated'),
        (VALIDATED, 'Validated'),
        (DOWNLOADED, 'Downloaded'),
    ]

    internship = models.OneToOneField(Internship, on_delete=models.CASCADE, related_name='agreement')
    admin = models.ForeignKey(Admin, on_delete=models.SET_NULL, null=True, related_name='agreements')
    generationDate = models.DateField(auto_now_add=True)
    pdfUrl = models.FileField(upload_to='agreements/', blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=GENERATED)

    def __str__(self):
        return f"Agreement: {self.internship}"

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Notification for {self.user.email}"