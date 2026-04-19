from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User, Student, Company, DEPARTMENT_CHOICES
from offers.models import Skill 
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

# ── CUSTOM JWT: INSTITUTIONAL SCOPING ──
# Logic: We override the standard JWT to include the user's role and department.
# This allows the React frontend to determine if the user is the Dean or a 
# Department Head instantly upon login without extra API calls.
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user.role
        
        # Security Logic: If the user has an admin profile, we attach their 
        # department ID. If it's NULL, the frontend identifies them as the Dean.
        if hasattr(user, 'admin'):
            token['department'] = user.admin.department
        return token

# ── STUDENT REGISTRATION ──
class StudentRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ['email', 'password']

    def validate_email(self, value):
        # Business Rule: Ensuring academic domain integrity.
        if not value.endswith('.dz'):
            raise serializers.ValidationError("Please use your university email address (.dz domain).")
        return value

    def create(self, validated_data):
        # Transactional Logic: Creating the Auth account and the Student profile simultaneously.
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
            # Data Isolation: Capturing the student's department (IFA/TLSI/MI) at birth.
            department=req.get('department'),
        )
        return user

# ── COMPANY REGISTRATION ──
class CompanyRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ['email', 'password']

    def create(self, validated_data):
        # MULTIPART HANDLING: Separating JSON data from the PDF file stream.
        req = self.context['request'].data
        files = self.context['request'].FILES
        
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
            # Legal Proof: Attaching the Registre de Commerce PDF for the Dean's audit.
            registreCommerce=files.get('registreCommerce'),
        )
        return user

# ── STUDENT PROFILE UPDATE ──
class StudentUpdateSerializer(serializers.ModelSerializer):
    # Relational Logic: PrimaryKeyRelatedField allows the frontend to send a list 
    # of IDs [1, 3, 5] instead of raw text, maintaining database normalization.
    skills = serializers.PrimaryKeyRelatedField(
        many=True, 
        queryset=Skill.objects.all(), 
        required=False
    )

    class Meta:
        model = Student
        fields = [
            'phoneNumber',
            'univWillaya',
            'githubLink',
            'portfolioLink',
            'IDCardNumber',
            'socialSecurityNumber', # Vital for the automated agreement
            'department',
            'skills',
        ]

    def update(self, instance, validated_data):
        # M2M Synchronization: Many-to-Many fields require the .set() method
        # to update the hidden junction table safely.
        skill_ids = validated_data.pop('skills', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if skill_ids is not None:
            instance.skills.set(skill_ids)
        return instance

# ── COMPANY PROFILE UPDATE ──
class CompanyUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ['companyName', 'location', 'description', 'website', 'phoneNumber', 'registreCommerce']