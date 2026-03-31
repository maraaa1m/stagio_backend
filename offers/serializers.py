from rest_framework import serializers
from .models import InternshipOffer, Skill

class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ['id', 'skillName']

class InternshipOfferSerializer(serializers.ModelSerializer):
    requiredSkills = SkillSerializer(many=True, read_only=True)
    skillIds = serializers.ListField(
        child=serializers.CharField(),
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
            'startingDay',
            'deadline',
            'type',
            'requiredSkills',
            'skillIds',
        ]

    def create(self, validated_data):
        skill_ids = validated_data.pop('skillIds', [])
        offer = InternshipOffer.objects.create(**validated_data)
        for skill_id in skill_ids:
            try:
                skill = Skill.objects.get(id=skill_id)
                offer.requiredSkills.add(skill)
            except Skill.DoesNotExist:
                pass
        return offer

    def update(self, instance, validated_data):
        skill_ids = validated_data.pop('skillIds', [])
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if skill_ids:
            instance.requiredSkills.clear()
            for skill_id in skill_ids:
                try:
                    skill = Skill.objects.get(id=skill_id)
                    instance.requiredSkills.add(skill)
                except Skill.DoesNotExist:
                    pass
        return instance