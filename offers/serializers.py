from rest_framework import serializers
from .models import InternshipOffer, Skill
from django.utils import timezone

class SkillSerializer(serializers.ModelSerializer):
    """Logic: Standard mapping for the technical dictionary."""
    class Meta:
        model = Skill
        fields = ['id', 'skillName']

class InternshipOfferSerializer(serializers.ModelSerializer):
    """
    LOGIC: The Operational Orchestrator.
    Manages the data flow for internship listings, including capacity 
    tracking and temporal validation.
    """
    requiredSkills = SkillSerializer(many=True, read_only=True)
    
    # Logic: Read-only counter derived from the model's database-count property.
    remainingSpots = serializers.IntegerField(read_only=True)
    
    # Input Logic: Accepts an array of integers [1, 4, 8] for M2M links.
    skillIds = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = InternshipOffer
        fields = [
            'id', 
            'title', 
            'description', 
            'willaya', 
            'type',
            'maxParticipants',     
            'remainingSpots',      
            'is_active',           
            'applicationDeadline',  
            'internshipStartDate', 
            'internshipEndDate',   
            'requiredSkills', 
            'skillIds',
        ]

    def validate(self, data):
        """
        BUSINESS RULE: Temporal Integrity Check.
        Logic: Ensures that students have a realistic window to apply before 
        the work phase begins.
        """
        if data.get('applicationDeadline') and data.get('internshipStartDate'):
            if data['applicationDeadline'] >= data['internshipStartDate']:
                raise serializers.ValidationError({
                    "applicationDeadline": "The recruitment deadline must occur before the internship start date."
                })
        return data

    def create(self, validated_data):
        # Transaction logic: Separate Skill IDs from the primary Offer attributes
        skill_ids = validated_data.pop('skillIds', [])
        offer = InternshipOffer.objects.create(**validated_data)
        
        # Link to technical tags
        for skill_id in skill_ids:
            try:
                skill = Skill.objects.get(id=skill_id)
                offer.requiredSkills.add(skill)
            except Skill.DoesNotExist:
                pass
        return offer

    def update(self, instance, validated_data):
        # Synchronization logic: Re-mapping requirements during an edit
        skill_ids = validated_data.pop('skillIds', [])
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        if skill_ids is not None:
            # Atomic Sync: Clear old links to ensure no 'Ghost Skills' remain
            instance.requiredSkills.clear()
            for skill_id in skill_ids:
                try:
                    skill = Skill.objects.get(id=skill_id)
                    instance.requiredSkills.add(skill)
                except Skill.DoesNotExist:
                    pass
        return instance