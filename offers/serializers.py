from rest_framework import serializers
from .models import InternshipOffer, Skill

# --- THE SKILL TRANSLATOR ---
# Logic: A simple mapping to convert Skill objects into JSON (ID and Name).
class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ['id', 'skillName']

# --- THE INTERNSHIP OFFER ORCHESTRATOR ---
# Logic: This is a "Hybrid Serializer". It handles nested data for display 
# and a flat list of IDs for database creation.
class InternshipOfferSerializer(serializers.ModelSerializer):
    
    # NESTED OUTPUT: When the Frontend "Reads" an offer, it needs the full skill objects
    # (e.g., {"id": 1, "skillName": "React"}). 'read_only=True' ensures safety.
    requiredSkills = SkillSerializer(many=True, read_only=True)
    
    # LOGIC INPUT: When the Frontend "Writes" (creates/updates) an offer, it only sends 
    # a list of IDs (e.g., [1, 2, 5]). 'write_only=True' keeps the response clean.
    skillIds = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = InternshipOffer
        fields = [
            'id', 'title', 'description', 'willaya', 
            'startingDay', 'deadline', 'type', 
            'requiredSkills', 'skillIds',
        ]

    # TRANSACTION LOGIC: Overriding the Create method
    # Reason: Django's default create cannot handle Many-to-Many links automatically 
    # when data is sent as a list of IDs. We must orchestrate it manually.
    def create(self, validated_data):
        # 1. Extract the IDs from the data and remove them from the 'Offer' dictionary.
        skill_ids = validated_data.pop('skillIds', [])
        
        # 2. Create the physical Offer record in the database.
        offer = InternshipOffer.objects.create(**validated_data)
        
        # 3. Establish the Many-to-Many links.
        for skill_id in skill_ids:
            try:
                skill = Skill.objects.get(id=skill_id)
                offer.requiredSkills.add(skill) # Links the offer to the skill in the junction table
            except Skill.DoesNotExist:
                pass # Safety check to prevent the whole request from crashing if an ID is wrong
        return offer

    # UPDATE LOGIC: Synchronizing the Skill Set
    # Reason: When a company edits an offer, the skills might change completely.
    def update(self, instance, validated_data):
        skill_ids = validated_data.pop('skillIds', [])
        
        # 1. Update the standard fields (Title, Description, etc.)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # 2. Refresh the Many-to-Many relationships
        if skill_ids:
            instance.requiredSkills.clear() # Wipe the old skills to ensure a clean sync
            for skill_id in skill_ids:
                try:
                    skill = Skill.objects.get(id=skill_id)
                    instance.requiredSkills.add(skill)
                except Skill.DoesNotExist:
                    pass
        return instance