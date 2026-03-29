from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    STUDENT = 'STUDENT'
    COMPANY = 'COMPANY'
    ADMIN = 'ADMIN'

    ROLE_CHOICES = [
        (STUDENT, 'Student'),
        (COMPANY, 'Company'),
        (ADMIN, 'Admin'),
    ]

    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        null=True,
        blank=True
    )

    def __str__(self):
        return self.email


class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    firstName = models.CharField(max_length=100)
    lastName = models.CharField(max_length=100)
    IDCardNumber = models.CharField(max_length=50, unique=True)
    phoneNumber = models.CharField(max_length=20)
    githubLink = models.URLField(blank=True, null=True)
    portfolioLink = models.URLField(blank=True, null=True)
    cvFile = models.FileField(upload_to='cvs/', blank=True, null=True)
    univWillaya = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.firstName} {self.lastName}"


class Company(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    companyName = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    logoUrl = models.URLField(blank=True, null=True)
    location = models.CharField(max_length=100)
    website = models.URLField(blank=True, null=True)
    phoneNumber = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return self.companyName


class Admin(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    firstName = models.CharField(max_length=100)
    lastName = models.CharField(max_length=100)
    university = models.CharField(max_length=200)
    faculty = models.CharField(max_length=200)
    department = models.CharField(max_length=200)

    def __str__(self):
        return f"{self.firstName} {self.lastName}"