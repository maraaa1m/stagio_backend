from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """
    Logic: Core Authentication Identity.
    Decoupled from profiles to allow for role-based security branching.
    """
    STUDENT = 'STUDENT'
    COMPANY = 'COMPANY'
    ADMIN = 'ADMIN'
    ROLE_CHOICES = [(STUDENT, 'Student'), (COMPANY, 'Company'), (ADMIN, 'Admin')]
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, null=True, blank=True)

    def __str__(self):
        return self.email

# --- INSTITUTIONAL CONSTANTS ---
DEPARTMENT_CHOICES = [
    ('IFA', 'Informatique Fondamentale et ses Applications (IFA)'),
    ('MI', 'Mathématiques et Informatique (MI)'),
    ('TLSI', 'Technologies des Logiciels et Systèmes d’Information (TLSI)'),
]

class Student(models.Model):
    """
    Logic: The Academic Profile.
    Hardened with 'department' and 'socialSecurityNumber' for legal compliance.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    firstName = models.CharField(max_length=100)
    lastName = models.CharField(max_length=100)
    IDCardNumber = models.CharField(max_length=50, unique=True, null=True, blank=True)
    socialSecurityNumber = models.CharField(max_length=50, unique=True, null=True, blank=True)
    phoneNumber = models.CharField(max_length=20)
    githubLink = models.URLField(blank=True, null=True)
    portfolioLink = models.URLField(blank=True, null=True)
    
    # Files are stored on the server's filesystem; DB stores the path string.
    cvFile = models.FileField(upload_to='cvs/', blank=True, null=True)
    profile_photo = models.ImageField(upload_to='photos/', blank=True, null=True)
    
    univWillaya = models.CharField(max_length=100)
    department = models.CharField(
        max_length=10, 
        choices=DEPARTMENT_CHOICES, 
        null=True, 
        blank=True
    )
    
    skills = models.ManyToManyField(
        'offers.Skill',
        blank=True,
        related_name='students'
    )

    def __str__(self):
        return f"{self.firstName} {self.lastName} ({self.department})"


class Company(models.Model):
    """
    Logic: The Economic Sector Profile.
    Uses 'registreCommerce' FileField to satisfy the Dean's audit requirement.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    companyName = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    logo = models.ImageField(upload_to='logos/', blank=True, null=True)
    
    # MASTER FIX: Corporate Legal Identity (PDF/Image)
    registreCommerce = models.FileField(
        upload_to='registres/', 
        blank=True, 
        null=True
    )
    
    location = models.CharField(max_length=100)
    website = models.URLField(blank=True, null=True)
    phoneNumber = models.CharField(max_length=20, blank=True, null=True)
    
    # Governance Flags
    isApproved = models.BooleanField(default=False)
    isBlacklisted = models.BooleanField(default=False)

    def __str__(self):
        return self.companyName

class Admin(models.Model):
    """
    Logic: Institutional Governance.
    Department = NULL identifies the Dean (Doyen).
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='admin')
    firstName = models.CharField(max_length=100)
    lastName = models.CharField(max_length=100)
    university = models.CharField(max_length=200)
    faculty = models.CharField(max_length=200)
    department = models.CharField(
        max_length=10, 
        choices=DEPARTMENT_CHOICES, 
        null=True, 
        blank=True
    )

    @property
    def is_dean(self):
        return not self.department

    def __str__(self):
        role = "Dean" if self.is_dean else f"Head of {self.department}"
        return f"{self.firstName} {self.lastName} ({role})"