from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Application
from .serializers import ApplicationSerializer
from accounts.models import Student
from offers.models import InternshipOffer
from utils.matching import calculate_matching_score
from accounts.models import Student, Company


@api_view(['POST'])
def apply_to_offer(request):
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return Response(
            {'error': 'Only students can apply'},
            status=status.HTTP_403_FORBIDDEN
        )

    offer_id = request.data.get('offer_id')
    try:
        offer = InternshipOffer.objects.get(id=offer_id)
    except InternshipOffer.DoesNotExist:
        return Response(
            {'error': 'Offer not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    if Application.objects.filter(student=student, offer=offer).exists():
        return Response(
            {'error': 'You already applied to this offer'},
            status=status.HTTP_400_BAD_REQUEST
        )

    score = calculate_matching_score(student, offer)

    Application.objects.create(
        student=student,
        offer=offer,
        matchingScore=score,
        applicationStatus='PENDING'
    )

    return Response({
        'message': 'Application submitted successfully',
        'matchingScore': score,
        'status': 'PENDING'
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def get_application(request, application_id):
    try:
        application = Application.objects.get(
            id=application_id,
            student__user=request.user
        )
        serializer = ApplicationSerializer(application)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Application.DoesNotExist:
        return Response(
            {'error': 'Application not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
def get_company_applications(request):
    try:
        company = Company.objects.get(user=request.user)
    except Company.DoesNotExist:
        return Response(
            {'error': 'Only companies can view applications'},
            status=status.HTTP_403_FORBIDDEN
        )

    applications = Application.objects.filter(
        offer__company=company
    ).order_by('-matchingScore')

    data = []
    for app in applications:
        data.append({
            'application_id': app.id,
            'status': app.applicationStatus,
            'matchingScore': app.matchingScore,
            'applicationDate': app.applicationDate,
            'student': {
                'firstName': app.student.firstName,
                'lastName': app.student.lastName,
                'email': app.student.user.email,
                'githubLink': app.student.githubLink,
                'portfolioLink': app.student.portfolioLink,
                'skills': [s.skillName for s in app.student.skills.all()],
            },
            'offer': {
                'title': app.offer.title,
                'willaya': app.offer.willaya,
            }
        })

    return Response(data, status=status.HTTP_200_OK)