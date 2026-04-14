from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User, Student, Company
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


# ── Custom JWT: embeds user role so frontend can decode it ─────────────────────
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user.role
        return token


# ── Student registration ───────────────────────────────────────────────────────
class StudentRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
    )

    class Meta:
        model = User
        fields = ['email', 'password']

    def validate_email(self, value):
        if not value.endswith('.dz'):
            raise serializers.ValidationError(
                "Please use your university email address (.dz domain)."
            )
        return value

    def create(self, validated_data):
        req = self.context['request'].data
        user = User.objects.create_user(
            username=validated_data['email'],
            email=validated_data['email'],
            password=validated_data['password'],
            role=User.STUDENT,
        )
        Student.objects.create(
            user=user,
            firstName=req.get('firstName', ''),
            lastName=req.get('lastName', ''),
            phoneNumber=req.get('phoneNumber', ''),
            univWillaya=req.get('univWillaya', ''),
        )
        return user


# ── Company registration ───────────────────────────────────────────────────────
class CompanyRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
    )

    class Meta:
        model = User
        fields = ['email', 'password']

    def create(self, validated_data):
        req = self.context['request'].data
        user = User.objects.create_user(
            username=validated_data['email'],
            email=validated_data['email'],
            password=validated_data['password'],
            role=User.COMPANY,
        )
        Company.objects.create(
            user=user,
            companyName=req.get('companyName', ''),
            description=req.get('description', ''),
            location=req.get('location', ''),
            website=req.get('website', ''),
            phoneNumber=req.get('phoneNumber', ''),
        )
        return user


# ── Student profile update ─────────────────────────────────────────────────────
# Skills are handled manually in the view (M2M can't be set via serializer.save()).
# We list them here only so partial=True doesn't reject the key if it arrives.
class StudentUpdateSerializer(serializers.ModelSerializer):
    # Accept a list of skill IDs from the frontend; write_only so they don't
    # appear in the response (the view re-fetches the full profile after saving).
    skills = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        write_only=True,
    )

    class Meta:
        model = Student
        fields = [
            'phoneNumber',
            'univWillaya',
            'githubLink',
            'portfolioLink',
            'IDCardNumber',
            'skills',
        ]

    def update(self, instance, validated_data):
        # Pop skills before calling super() — M2M must be handled separately
        skill_ids = validated_data.pop('skills', None)

        # Update the scalar fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Sync the M2M relationship
        if skill_ids is not None:
            instance.skills.set(skill_ids)

        return instance


# ── Company profile update ─────────────────────────────────────────────────────
class CompanyUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ['companyName', 'location', 'description', 'website', 'phoneNumber']