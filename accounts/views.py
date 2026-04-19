from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import (
    StudentRegisterSerializer,
    CompanyRegisterSerializer,
    StudentUpdateSerializer,
    CompanyUpdateSerializer,
    CustomTokenObtainPairSerializer,
)
from .models import Student, Company, User
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import send_mail

# ── CUSTOM LOGIN ──
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

# ── HELPER: TOKEN ISSUANCE ──
def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    refresh['role'] = user.role
    return {
        'refresh': str(refresh),
        'access':  str(refresh.access_token),
    }

# ── HELPER: CANONICAL DATA ORCHESTRATOR ──
def _build_student_profile(student, request):
    """
    Logic: Ensures all media paths are converted to Absolute URIs.
    This allows the React Frontend to find the files on the laptop storage.
    """
    def get_abs_url(field):
        if not field:
            return None
        return request.build_absolute_uri(field.url)

    return {
        'email':         student.user.email,
        'firstName':     student.firstName,
        'lastName':      student.lastName,
        'phoneNumber':   student.phoneNumber,
        'univWillaya':   student.univWillaya,
        'githubLink':    student.githubLink or '',
        'portfolioLink': student.portfolioLink or '',
        
        # MEDIA ASSETS (Absolute Links)
        'photo':         get_abs_url(student.profile_photo),
        'cv':            get_abs_url(student.cvFile),
        
        # INSTITUTIONAL METADATA
        'department':           student.department,
        'departmentLabel':      student.get_department_display(),
        'socialSecurityNumber': student.socialSecurityNumber or 'Not Provided',
        'IDCardNumber':         student.IDCardNumber or 'Not Provided',
        
        # SKILL MATRIX
        'skills':        [{'id': s.id, 'skillName': s.skillName} for s in student.skills.all()],
    }

# ── ONBOARDING ──

@api_view(['POST'])
@permission_classes([AllowAny])
def register_student(request):
    serializer = StudentRegisterSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        user   = serializer.save()
        tokens = get_tokens_for_user(user)
        return Response({'message': 'Success', **tokens}, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser])
def register_company(request):
    """Logic: Accepts the Registre de Commerce PDF stream during registration."""
    serializer = CompanyRegisterSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        user   = serializer.save()
        tokens = get_tokens_for_user(user)
        return Response({'message': 'Company registered successfully', **tokens}, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# ── STUDENT OPERATIONS ──

@api_view(['GET'])
def get_student_profile(request):
    try:
        student = Student.objects.get(user=request.user)
        return Response(_build_student_profile(student, request), status=status.HTTP_200_OK)
    except Student.DoesNotExist:
        return Response({'error': 'Not found'}, status=404)

@api_view(['PUT'])
def update_student_profile(request):
    try:
        student    = Student.objects.get(user=request.user)
        serializer = StudentUpdateSerializer(student, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Updated', 'data': _build_student_profile(student, request)}, status=200)
        return Response(serializer.errors, status=400)
    except Student.DoesNotExist:
        return Response(status=404)

@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def upload_student_photo(request):
    try:
        student = Student.objects.get(user=request.user)
        if 'photo' not in request.FILES: return Response(status=400)
        student.profile_photo = request.FILES['photo']
        student.save()
        return Response({'url': request.build_absolute_uri(student.profile_photo.url)})
    except:
        return Response(status=404)

@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def upload_cv(request):
    try:
        student = Student.objects.get(user=request.user)
        if 'cv' not in request.FILES: return Response(status=400)
        student.cvFile = request.FILES['cv']
        student.save()
        return Response({'url': request.build_absolute_uri(student.cvFile.url)})
    except:
        return Response(status=404)

# ── COMPANY OPERATIONS ──

@api_view(['GET'])
def get_company_profile(request):
    try:
        company = Company.objects.get(user=request.user)
        return Response({
            'email':            request.user.email,
            'companyName':      company.companyName,
            'description':      company.description or '',
            'logo':             request.build_absolute_uri(company.logo.url) if company.logo else None,
            'registreCommerce': request.build_absolute_uri(company.registreCommerce.url) if company.registreCommerce else None,
            'location':         company.location,
            'website':          company.website or '',
            'phoneNumber':      company.phoneNumber or '',
            'isApproved':       company.isApproved,
        })
    except Company.DoesNotExist:
        return Response(status=404)

@api_view(['PUT'])
def update_company_profile(request):
    try:
        company    = Company.objects.get(user=request.user)
        serializer = CompanyUpdateSerializer(company, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Success'})
        return Response(serializer.errors, status=400)
    except Company.DoesNotExist:
        return Response(status=404)

@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def upload_company_logo(request):
    try:
        company = Company.objects.get(user=request.user)
        if 'logo' not in request.FILES: return Response(status=400)
        company.logo = request.FILES['logo']
        company.save()
        return Response({'url': request.build_absolute_uri(company.logo.url)})
    except:
        return Response(status=404)

# ── SECURITY UTILITIES ──

@api_view(['POST'])
def logout(request):
    try:
        token = RefreshToken(request.data.get('refresh'))
        token.blacklist()
        return Response({'message': 'Logged out'}, status=200)
    except:
        return Response(status=400)

@api_view(['POST'])
@permission_classes([AllowAny])
def forgot_password(request):
    email = request.data.get('email', '').strip()
    try:
        user  = User.objects.get(email=email)
        token = default_token_generator.make_token(user)
        uid   = urlsafe_base64_encode(force_bytes(user.pk))
        reset_url = f"http://localhost:5173/reset-password/{uid}/{token}/"
        send_mail('Password Reset', f'Click here: {reset_url}', 'noreply@stag.io', [email])
    except:
        pass # Enumeration protection
    return Response({'message': 'Email sent if account exists.'})

@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request):
    uidb64, token, new_password = request.data.get('uid'), request.data.get('token'), request.data.get('new_password')
    try:
        uid  = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
        if default_token_generator.check_token(user, token):
            user.set_password(new_password)
            user.save()
            return Response({'message': 'Success'})
        return Response({'error': 'Invalid token'}, status=400)
    except:
        return Response(status=400)