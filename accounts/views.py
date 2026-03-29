from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from .serializers import StudentRegisterSerializer, CompanyRegisterSerializer, StudentUpdateSerializer, CompanyUpdateSerializer
from .models import Student, Company


def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


@api_view(['POST'])
@permission_classes([AllowAny])
def register_student(request):
    serializer = StudentRegisterSerializer(
        data=request.data,
        context={'request': request}
    )
    if serializer.is_valid():
        user = serializer.save()
        tokens = get_tokens_for_user(user)
        return Response({
            'message': 'Student registered successfully',
            'tokens': tokens
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def register_company(request):
    serializer = CompanyRegisterSerializer(
        data=request.data,
        context={'request': request}
    )
    if serializer.is_valid():
        user = serializer.save()
        tokens = get_tokens_for_user(user)
        return Response({
            'message': 'Company registered successfully — awaiting admin approval',
            'tokens': tokens
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_student_profile(request):
    try:
        student = Student.objects.get(user=request.user)
        data = {
            'email': request.user.email,
            'firstName': student.firstName,
            'lastName': student.lastName,
            'phoneNumber': student.phoneNumber,
            'univWillaya': student.univWillaya,
            'githubLink': student.githubLink,
            'portfolioLink': student.portfolioLink,
        }
        return Response(data, status=status.HTTP_200_OK)
    except Student.DoesNotExist:
        return Response(
            {'error': 'Student not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
def logout(request):
    try:
        refresh_token = request.data.get('refresh')
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response(
            {'message': 'Logged out successfully'},
            status=status.HTTP_200_OK
        )
    except TokenError:
        return Response(
            {'error': 'Invalid token'},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['PUT'])
def update_student_profile(request):
    try:
        student = Student.objects.get(user=request.user)
        serializer = StudentUpdateSerializer(
            student,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Profile updated successfully',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Student.DoesNotExist:
        return Response(
            {'error': 'Student not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
def get_company_profile(request):
    try:
        company = Company.objects.get(user=request.user)
        data = {
            'email': request.user.email,
            'companyName': company.companyName,
            'description': company.description,
            'logoUrl': company.logoUrl,
            'location': company.location,
            'website': company.website,
            'phoneNumber': company.phoneNumber,
        }
        return Response(data, status=status.HTTP_200_OK)
    except Company.DoesNotExist:
        return Response(
            {'error': 'Company not found!'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['PUT'])
def update_company_profile(request):
    try:
        company = Company.objects.get(user=request.user)
        serializer = CompanyUpdateSerializer(
            company,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Profile updated successfully',
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    except Company.DoesNotExist:
        return Response(
            {'error': 'Company not found!'},
            status=status.HTTP_404_NOT_FOUND
        )