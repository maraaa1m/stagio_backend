from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import User, Company, Admin
from accounts.models import User, Company, Admin, Student
from applications.models import Application
from offers.models import InternshipOffer


@api_view(['GET'])
def get_pending_companies(request):
    try:
        Admin.objects.get(user=request.user)
    except Admin.DoesNotExist:
        return Response(
            {'error': 'Admin access required'},
            status=status.HTTP_403_FORBIDDEN
        )

    companies = Company.objects.filter(isApproved=False)
    data = []
    for company in companies:
        data.append({
            'id': company.id,
            'companyName': company.companyName,
            'email': company.user.email,
            'location': company.location,
            'description': company.description,
            'website': company.website,
        })
    return Response(data, status=status.HTTP_200_OK)


@api_view(['PUT'])
def approve_company(request, company_id):
    try:
        Admin.objects.get(user=request.user)
    except Admin.DoesNotExist:
        return Response(
            {'error': 'Admin access required'},
            status=status.HTTP_403_FORBIDDEN
        )

    try:
        company = Company.objects.get(id=company_id)
        company.isApproved = True
        company.save()
        return Response(
            {'message': f'{company.companyName} approved successfully'},
            status=status.HTTP_200_OK
        )
    except Company.DoesNotExist:
        return Response(
            {'error': 'Company not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['PUT'])
def refuse_company(request, company_id):
    try:
        Admin.objects.get(user=request.user)
    except Admin.DoesNotExist:
        return Response(
            {'error': 'Admin access required'},
            status=status.HTTP_403_FORBIDDEN
        )
    try:
        company = Company.objects.get(id=company_id)
        reason = request.data.get('reason', 'Company did not meet our requirements')
        company.delete()
        return Response({
            'message': f'Company refused. Reason: {reason}'
        }, status=status.HTTP_200_OK)
    except Company.DoesNotExist:
        return Response(
            {'error': 'Company not found'},
            status=status.HTTP_404_NOT_FOUND
        )



@api_view(['GET'])
def get_statistics(request):
    try:
        Admin.objects.get(user=request.user)
    except Admin.DoesNotExist:
        return Response(
            {'error': 'Admin access required'},
            status=status.HTTP_403_FORBIDDEN
        )

    total_students = Student.objects.count()
    placed = Application.objects.filter(
        applicationStatus='VALIDATED'
    ).values('student').distinct().count()
    unplaced = total_students - placed

    data = {
        'total_students': total_students,
        'placed_students': placed,
        'unplaced_students': unplaced,
        'total_companies': Company.objects.filter(isApproved=True).count(),
        'total_offers': InternshipOffer.objects.count(),
        'total_applications': Application.objects.count(),
        'pending_applications': Application.objects.filter(applicationStatus='PENDING').count(),
        'accepted_applications': Application.objects.filter(applicationStatus='ACCEPTED').count(),
    }

    return Response(data, status=status.HTTP_200_OK)