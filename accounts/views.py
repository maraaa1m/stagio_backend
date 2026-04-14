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


# ── Custom login view (embeds role in JWT) ─────────────────────────────────────
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


# ── Helpers ────────────────────────────────────────────────────────────────────
def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    refresh['role'] = user.role
    return {
        'refresh': str(refresh),
        'access':  str(refresh.access_token),
    }


def _build_student_profile(student, request):
    """Return the canonical student profile dict used in every GET response."""
    request_scheme = request.scheme if request else 'http'
    request_host   = request.get_host() if request else 'localhost:8000'
    base_url       = f"{request_scheme}://{request_host}"

    def abs_url(field):
        if not field:
            return None
        url = field.url
        return url if url.startswith('http') else f"{base_url}{url}"

    return {
        'email':         student.user.email,
        'firstName':     student.firstName,
        'lastName':      student.lastName,
        'phoneNumber':   student.phoneNumber,
        'univWillaya':   student.univWillaya,
        'githubLink':    student.githubLink or '',
        'portfolioLink': student.portfolioLink or '',
        'photo':         abs_url(student.profile_photo),
        'cv':            abs_url(student.cvFile),
        'skills':        [{'id': s.id, 'skillName': s.skillName} for s in student.skills.all()],
    }


# ── Registration ───────────────────────────────────────────────────────────────
@api_view(['POST'])
@permission_classes([AllowAny])
def register_student(request):
    serializer = StudentRegisterSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        user   = serializer.save()
        tokens = get_tokens_for_user(user)
        return Response(
            {'message': 'Student registered successfully', **tokens},
            status=status.HTTP_201_CREATED,
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def register_company(request):
    serializer = CompanyRegisterSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        user   = serializer.save()
        tokens = get_tokens_for_user(user)
        return Response(
            {'message': 'Company registered successfully — awaiting admin approval', **tokens},
            status=status.HTTP_201_CREATED,
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ── Student profile ────────────────────────────────────────────────────────────
@api_view(['GET'])
def get_student_profile(request):
    try:
        student = Student.objects.get(user=request.user)
        return Response(_build_student_profile(student, request), status=status.HTTP_200_OK)
    except Student.DoesNotExist:
        return Response({'error': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['PUT'])
def update_student_profile(request):
    try:
        student    = Student.objects.get(user=request.user)
        serializer = StudentUpdateSerializer(student, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            # Return the full, refreshed profile so frontend can update state
            return Response(
                {
                    'message': 'Profile updated successfully',
                    'data':    _build_student_profile(student, request),
                },
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Student.DoesNotExist:
        return Response({'error': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def upload_student_photo(request):
    try:
        student = Student.objects.get(user=request.user)
        if 'photo' not in request.FILES:
            return Response({'error': 'No photo provided'}, status=status.HTTP_400_BAD_REQUEST)
        student.profile_photo = request.FILES['photo']
        student.save()
        url = request.build_absolute_uri(student.profile_photo.url)
        return Response({'message': 'Photo uploaded', 'url': url}, status=status.HTTP_200_OK)
    except Student.DoesNotExist:
        return Response({'error': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def upload_cv(request):
    try:
        student = Student.objects.get(user=request.user)
        if 'cv' not in request.FILES:
            return Response({'error': 'No CV file provided'}, status=status.HTTP_400_BAD_REQUEST)
        student.cvFile = request.FILES['cv']
        student.save()
        url = request.build_absolute_uri(student.cvFile.url)
        return Response({'message': 'CV uploaded successfully', 'url': url}, status=status.HTTP_200_OK)
    except Student.DoesNotExist:
        return Response({'error': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)


# ── Company profile ────────────────────────────────────────────────────────────
@api_view(['GET'])
def get_company_profile(request):
    try:
        company = Company.objects.get(user=request.user)
        logo_url = None
        if company.logo:
            logo_url = request.build_absolute_uri(company.logo.url)
        data = {
            'email':       request.user.email,
            'companyName': company.companyName,
            'description': company.description or '',
            'logo':        logo_url,
            'location':    company.location,
            'website':     company.website or '',
            'phoneNumber': company.phoneNumber or '',
            'isApproved':  company.isApproved,
        }
        return Response(data, status=status.HTTP_200_OK)
    except Company.DoesNotExist:
        return Response({'error': 'Company not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['PUT'])
def update_company_profile(request):
    try:
        company    = Company.objects.get(user=request.user)
        serializer = CompanyUpdateSerializer(company, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {'message': 'Profile updated successfully'},
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Company.DoesNotExist:
        return Response({'error': 'Company not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@parser_classes([MultiPartParser, FormParser])
def upload_company_logo(request):
    try:
        company = Company.objects.get(user=request.user)
        if 'logo' not in request.FILES:
            return Response({'error': 'No logo provided'}, status=status.HTTP_400_BAD_REQUEST)
        company.logo = request.FILES['logo']
        company.save()
        url = request.build_absolute_uri(company.logo.url)
        return Response({'message': 'Logo uploaded', 'url': url}, status=status.HTTP_200_OK)
    except Company.DoesNotExist:
        return Response({'error': 'Company not found'}, status=status.HTTP_404_NOT_FOUND)


# ── Auth ───────────────────────────────────────────────────────────────────────
@api_view(['POST'])
def logout(request):
    try:
        token = RefreshToken(request.data.get('refresh'))
        token.blacklist()
        return Response({'message': 'Logged out successfully'}, status=status.HTTP_200_OK)
    except TokenError:
        return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def forgot_password(request):
    email = request.data.get('email', '').strip()
    # Always respond 200 to prevent user enumeration
    try:
        user  = User.objects.get(email=email)
        token = default_token_generator.make_token(user)
        uid   = urlsafe_base64_encode(force_bytes(user.pk))
        reset_url = f"http://localhost:5173/reset-password/{uid}/{token}/"
        send_mail(
            subject='Reset your Stag.io password',
            message=f'Click the link below to reset your password:\n\n{reset_url}\n\nThis link expires in 24 hours.',
            from_email='noreply@stag.io',
            recipient_list=[email],
            fail_silently=True,
        )
    except User.DoesNotExist:
        pass  # Don't reveal whether the email exists
    return Response(
        {'message': 'If an account exists with this email, you will receive a reset link shortly.'},
        status=status.HTTP_200_OK,
    )


@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request):
    uidb64       = request.data.get('uid', '')
    token        = request.data.get('token', '')
    new_password = request.data.get('new_password', '')
    try:
        uid  = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
        if default_token_generator.check_token(user, token):
            user.set_password(new_password)
            user.save()
            return Response({'message': 'Password updated successfully'}, status=status.HTTP_200_OK)
        return Response({'error': 'Invalid or expired link'}, status=status.HTTP_400_BAD_REQUEST)
    except Exception:
        return Response({'error': 'Invalid request'}, status=status.HTTP_400_BAD_REQUEST)