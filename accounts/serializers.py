from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User, Student, Company


class StudentRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password]
    )

    class Meta:
        model = User
        fields = ['email', 'password']

    def validate_email(self, value):
        if not value.endswith('.dz'):
            raise serializers.ValidationError(
                "Invalid email, use your professional one"
            )
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['email'],
            email=validated_data['email'],
            password=validated_data['password'],
            role=User.STUDENT
        )
        Student.objects.create(
            user=user,
            firstName=self.context['request'].data.get('firstName'),
            lastName=self.context['request'].data.get('lastName'),
            phoneNumber=self.context['request'].data.get('phoneNumber'),
            univWillaya=self.context['request'].data.get('univWillaya'),
        )
        return user


class CompanyRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password]
    )

    class Meta:
        model = User
        fields = ['email', 'password']

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['email'],
            email=validated_data['email'],
            password=validated_data['password'],
            role=User.COMPANY
        )
        Company.objects.create(
            user=user,
            companyName=self.context['request'].data.get('companyName'),
            description=self.context['request'].data.get('description'),
            location=self.context['request'].data.get('location'),
            website=self.context['request'].data.get('website'),
        )
        return user


class StudentUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = [
            'phoneNumber',
            'univWillaya',
            'githubLink',
            'portfolioLink',
        ]
class CompanyUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = [
            'location',
            'logoUrl',
            'description',
            'website',
            'phoneNumber',
        ]