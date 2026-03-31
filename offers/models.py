from django.db import models
from accounts.models import Company, Student

class Skill(models.Model):
    skillName = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.skillName

class InternshipOffer(models.Model):
    ONLINE = 'ONLINE'
    IN_PERSON = 'IN_PERSON'

    TYPE_CHOICES = [
        (ONLINE, 'Online'),
        (IN_PERSON, 'In Person'),
    ]

    company = models.ForeignKey(
        Company, 
        on_delete=models.CASCADE,
        related_name='offers'
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    willaya = models.CharField(max_length=100)
    startingDay = models.DateField()
    deadline = models.DateField()
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    requiredSkills = models.ManyToManyField(
        Skill,
        related_name='offers'
    )

    def __str__(self):
        return self.title
