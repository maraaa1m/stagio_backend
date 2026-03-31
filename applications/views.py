from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Application, Internship, Agreement, Notification
from .serializers import ApplicationSerializer, NotificationSerializer
from accounts.models import Student, Company, Admin, User
from offers.models import InternshipOffer
from utils.matching import calculate_matching_score
from utils.pdf_generator import generate_agreement_pdf

@api_view(['POST'])
def apply_to_offer(request):
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return Response({'error': 'Only students can apply'}, status=status.HTTP_403_FORBIDDEN)

    offer_id = request.data.get('offer_id')
    offer = get_object_or_404(InternshipOffer, id=offer_id)

    if Application.objects.filter(student=student, offer=offer).exists():
        return Response({'error': 'You already applied to this offer'}, status=status.HTTP_400_BAD_REQUEST)

    score = calculate_matching_score(student, offer)
    Application.objects.create(student=student, offer=offer, matchingScore=score)

    return Response({'message': 'Application submitted successfully', 'matchingScore': score, 'status': 'PENDING'}, status=status.HTTP_201_CREATED)

@api_view(['GET'])
def get_application(request, application_id):
    try:
        application = Application.objects.get(id=application_id, student__user=request.user)
        serializer = ApplicationSerializer(application)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Application.DoesNotExist:
        return Response({'error': 'Application not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def get_student_applications(request):
    try:
        student = Student.objects.get(user=request.user)
        apps = Application.objects.filter(student=student).order_by('-applicationDate')
        data = []
        for a in apps:
            pdf_url = None
            if hasattr(a, 'internship') and hasattr(a.internship, 'agreement'):
                if a.internship.agreement.pdfUrl:
                    pdf_url = a.internship.agreement.pdfUrl.url
            data.append({
                'id': a.id,
                'offerTitle': a.offer.title,
                'company': a.offer.company.companyName,
                'status': a.applicationStatus,
                'matchingScore': a.matchingScore,
                'pdfUrl': pdf_url
            })
        return Response(data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def get_company_applications(request):
    try:
        company = Company.objects.get(user=request.user)
        applications = Application.objects.filter(offer__company=company).order_by('-matchingScore')
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
                    'skills': [s.skillName for s in app.student.skills.all()],
                },
                'offer': {'title': app.offer.title}
            })
        return Response(data, status=status.HTTP_200_OK)
    except Company.DoesNotExist:
        return Response({'error': 'Only companies can view applications'}, status=status.HTTP_403_FORBIDDEN)

@api_view(['PUT'])
def accept_application(request, application_id):
    try:
        company = Company.objects.get(user=request.user)
        app = Application.objects.get(id=application_id, offer__company=company)
    except (Company.DoesNotExist, Application.DoesNotExist):
        return Response({'error': 'Not found or unauthorized'}, status=status.HTTP_404_NOT_FOUND)

    if app.applicationStatus != 'PENDING':
        return Response({'error': 'Application already processed'}, status=status.HTTP_400_BAD_REQUEST)

    app.applicationStatus = 'ACCEPTED'
    app.save()

    Notification.objects.create(user=app.student.user, message=f"Application for {app.offer.title} has been ACCEPTED by {company.companyName}.")
    return Response({'message': 'Application accepted — university admin notified', 'status': 'ACCEPTED'}, status=status.HTTP_200_OK)

@api_view(['PUT'])
def refuse_application(request, application_id):
    try:
        company = Company.objects.get(user=request.user)
        app = Application.objects.get(id=application_id, offer__company=company)
    except (Company.DoesNotExist, Application.DoesNotExist):
        return Response({'error': 'Not found or unauthorized'}, status=status.HTTP_404_NOT_FOUND)

    if app.applicationStatus != 'PENDING':
        return Response({'error': 'Application already processed'}, status=status.HTTP_400_BAD_REQUEST)

    reason = request.data.get('reason', 'No reason provided')
    app.applicationStatus = 'REFUSED'
    app.save()

    Notification.objects.create(user=app.student.user, message=f"Your application for {app.offer.title} was REFUSED. Reason: {reason}")
    return Response({'message': f'Application refused. Reason: {reason}', 'status': 'REFUSED'}, status=status.HTTP_200_OK)

@api_view(['GET'])
def get_accepted_for_admin(request):
    try:
        Admin.objects.get(user=request.user)
        apps = Application.objects.filter(applicationStatus='ACCEPTED')
        data = [{'id': a.id, 'student': f"{a.student.firstName} {a.student.lastName}", 'company': a.offer.company.companyName, 'offer': a.offer.title} for a in apps]
        return Response(data, status=status.HTTP_200_OK)
    except Admin.DoesNotExist:
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)

@api_view(['POST'])
def admin_validate_internship(request, application_id):
    try:
        admin = Admin.objects.get(user=request.user)
        app = get_object_or_404(Application, id=application_id, applicationStatus='ACCEPTED')

        internship, created = Internship.objects.get_or_create(
            application=app,
            defaults={
                'startDate': app.offer.startingDay,
                'endDate': app.offer.deadline,
                'topic': app.offer.title,
                'supervisorName': f"Admin {admin.lastName}"
            }
        )

        pdf_file = generate_agreement_pdf(app, admin)

        Agreement.objects.update_or_create(
            internship=internship,
            defaults={'admin': admin, 'pdfUrl': pdf_file, 'status': 'VALIDATED'}
        )

        app.applicationStatus = 'VALIDATED'
        app.save()

        Notification.objects.create(user=app.student.user, message=f"Internship at {app.offer.company.companyName} is VALIDATED. PDF is ready.")
        return Response({'message': 'Internship validated and agreement generated!'}, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def get_notifications(request):
    notes = Notification.objects.filter(user=request.user).order_by('-created_at')
    serializer = NotificationSerializer(notes, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)