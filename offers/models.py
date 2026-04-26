from django.db import models
from datetime import date

# --- TECHNICAL DICTIONARY ---
class Skill(models.Model):
    """
    LOGIC: The Global Skill Repository.
    This model acts as a centralized dictionary for technical expertise. 
    By using a Many-to-Many relationship, we ensure that a single skill object 
    (e.g., 'React') is shared between students and offers, which is the 
    mathematical requirement for our Set-Theory matching engine.
    """
    skillName = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.skillName

# --- THE MARKETPLACE ENGINE ---
class InternshipOffer(models.Model):
    """
    LOGIC: The Intelligent Offer Model.
    This class manages the lifecycle of an internship advertisement and defines 
    the operational constraints (capacity and timing) of the placement.
    """
    ONLINE = 'ONLINE'
    IN_PERSON = 'IN_PERSON'
    TYPE_CHOICES = [(ONLINE, 'Online'), (IN_PERSON, 'In Person')]

    # RELATIONAL LINK: Decoupled via string reference to avoid circular imports.
    # One company can post multiple offers, but each offer belongs to one entity.
    company = models.ForeignKey(
        'accounts.Company', 
        on_delete=models.CASCADE,
        related_name='offers'
    )
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    # Logic Case 01: 'willaya' is used by the algorithm to block 'IN_PERSON' matches 
    # if the student studies in a different region.
    willaya = models.CharField(max_length=100) 
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    
    # --- RESOURCE MANAGEMENT LOGIC ---
    # maxParticipants: Sets the institutional limit for the number of interns.
    # is_active: A manual 'kill-switch' for the company to hide the offer.
    maxParticipants = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    
    # --- TEMPORAL ARCHITECTURE ---
    # RECRUITMENT PHASE: applicationDeadline defines when the student can no longer apply.
    applicationDeadline = models.DateField() 
    
    # OPERATIONAL PHASE: Start and End dates define the actual professional period.
    # These dates are automatically injected into the generated legal agreement.
    internshipStartDate = models.DateField()
    internshipEndDate = models.DateField()
    
    requiredSkills = models.ManyToManyField(
        Skill,
        related_name='offers'
    )

    class Meta:
        # UX Logic: Ensures that the newest opportunities appear first on the dashboard.
        ordering = ['-id']

    @property
    def is_recruitment_open(self):
        """
        LOGIC: Automated Lifecycle Guard.
        The offer is only 'Open' if it meets three conditions:
        1. Current date is before the deadline.
        2. There are still spots available (remainingSpots > 0).
        3. The offer has not been manually deactivated.
        """
        return date.today() <= self.applicationDeadline and self.remainingSpots > 0 and self.is_active

    @property
    def remainingSpots(self):
        """
        ALGORITHMIC LOGIC: The Saturation Monitor.
        Calculates real-time availability. A spot is only considered 'consumed' 
        once the University Admin VALIDATES the internship. This prevents 
        administrative over-booking when multiple students apply.
        """
        # Internal import to avoid circular dependency at the top of the file.
        from applications.models import Application
        validated_count = Application.objects.filter(
            offer=self, 
            applicationStatus='VALIDATED'
        ).count()
        return max(0, self.maxParticipants - validated_count)

    def __str__(self):
        return f"{self.title} @ {self.company.companyName}"