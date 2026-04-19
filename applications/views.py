from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.conf import settings

from .models import Application, Internship, Agreement, Notification
from .serializers import NotificationSerializer
from accounts.models import Student, Company, Admin
from offers.models import InternshipOffer
from utils.matching import calculate_matching_score
from utils.pdf_generator import generate_agreement_pdf

@api_view(['POST'])
def apply_to_offer(request):
    try:
        student = Student.objects.get(user=request.user)
        offer_id = request.data.get('offer_id')
        offer = get_object_or_404(InternshipOffer, id=offer_id)
        if Application.objects.filter(student=student, offer=offer).exists():
            return Response({'error': 'You already applied to this offer.'}, status=400)
        score = calculate_matching_score(student, offer)
        Application.objects.create(student=student, offer=offer, matchingScore=score)
        return Response({'message': 'Success', 'matchingScore': score}, status=201)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['GET'])
def get_student_applications(request):
    try:
        student = Student.objects.get(user=request.user)
        apps = Application.objects.filter(student=student).select_related('offer', 'offer__company').order_by('-applicationDate')
        data = []
        for a in apps:
            pdf_url = request.build_absolute_uri(a.internship.agreement.pdfUrl.url) if hasattr(a, 'internship') and hasattr(a.internship, 'agreement') and a.internship.agreement.pdfUrl else None
            data.append({
                'id': a.id,
                'offer_id': a.offer.id,
                'offerTitle': a.offer.title,
                'company': a.offer.company.companyName,
                'status': a.applicationStatus,
                'matchingScore': a.matchingScore,
                'appliedAt': str(a.applicationDate),
                'pdfUrl': pdf_url,
                'refusalReason': getattr(a, 'refusal_reason', None),
            })
        return Response(data)
    except Student.DoesNotExist:
        return Response({'error': 'Student not found.'}, status=404)

@api_view(['GET'])
def get_company_applications(request):
    """
    LOGIC: Evidence-Based Recruitment.
    The system now returns full student metadata (CV, GitHub, Portfolio) 
    so the recruiter can perform a detailed audit before making a decision.
    """
    try:
        company = Company.objects.get(user=request.user)
        apps = Application.objects.filter(offer__company=company).select_related('student', 'student__user').order_by('-matchingScore')
        data = []
        for a in apps:
            # Generate absolute URLs for the physical files stored on the laptop/server
            cv_url = request.build_absolute_uri(a.student.cvFile.url) if a.student.cvFile else None
            photo_url = request.build_absolute_uri(a.student.profile_photo.url) if a.student.profile_photo else None

            data.append({
                'id': a.id,
                'status': a.applicationStatus,
                'matchingScore': a.matchingScore,
                'student': {
                    'firstName': a.student.firstName,
                    'lastName': a.student.lastName,
                    'email': a.student.user.email,
                    'githubLink': a.student.githubLink or '',
                    'portfolioLink': a.student.portfolioLink or '',
                    'cv': cv_url, # THE KEY FOR THE RECRUITER
                    'photo': photo_url,
                    'skills': [s.skillName for s in a.student.skills.all()]
                },
                'offer': a.offer.title
            })
        return Response(data)
    except Company.DoesNotExist:
        return Response({'error': 'Unauthorized'}, status=403)

@api_view(['PUT'])
def accept_application(request, application_id):
    try:
        company = get_object_or_404(Company, user=request.user)
        app = get_object_or_404(Application, id=application_id, offer__company=company)
        app.applicationStatus = 'ACCEPTED'
        app.save()
        Notification.objects.create(user=app.student.user, message=f"Application for {app.offer.title} accepted by {company.companyName}.")
        return Response({'message': 'Accepted'})
    except:
        return Response(status=400)

@api_view(['PUT'])
def refuse_application(request, application_id):
    try:
        company = get_object_or_404(Company, user=request.user)
        app = get_object_or_404(Application, id=application_id, offer__company=company)
        reason = request.data.get('reason', 'No reason provided.')
        app.applicationStatus = 'REFUSED'
        if hasattr(app, 'refusal_reason'): app.refusal_reason = reason
        app.save()
        Notification.objects.create(user=app.student.user, message=f"Application refused by {company.companyName}. Reason: {reason}")
        return Response({'message': 'Refused'})
    except:
        return Response(status=400)

@api_view(['GET'])
def get_accepted_for_admin(request):
    try:
        admin_profile = Admin.objects.get(user=request.user)
        apps = Application.objects.filter(applicationStatus='ACCEPTED').select_related('student', 'offer', 'offer__company')
        if admin_profile.department:
            apps = apps.filter(student__department=admin_profile.department)
        data = [{'id': a.id, 'student': f"{a.student.firstName} {a.student.lastName}", 'dept': a.student.department, 'company': a.offer.company.companyName, 'offer': a.offer.title, 'score': a.matchingScore} for a in apps]
        return Response(data)
    except:
        return Response({'error': 'Unauthorized'}, status=403)

@api_view(['POST'])
def admin_validate_internship(request, application_id):
    try:
        admin = Admin.objects.get(user=request.user)
        query_params = {'id': application_id, 'applicationStatus': 'ACCEPTED'}
        if admin.department:
            query_params['student__department'] = admin.department
        app = get_object_or_404(Application, **query_params)
        
        internship, _ = Internship.objects.get_or_create(
            application=app,
            defaults={'startDate': app.offer.startingDay, 'endDate': app.offer.deadline, 'topic': app.offer.title, 'supervisorName': f"Admin {admin.lastName}"}
        )
        pdf_file = generate_agreement_pdf(app, admin)
        Agreement.objects.update_or_create(internship=internship, defaults={'admin': admin, 'pdfUrl': pdf_file, 'status': 'VALIDATED'})
        app.applicationStatus = 'VALIDATED'
        app.save()
        Notification.objects.create(user=app.student.user, message="Internship Validated! Your agreement is ready.")
        return Response({'message': 'Validated & PDF Generated'}, status=201)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['GET'])
def get_notifications(request):
    notes = Notification.objects.filter(user=request.user).order_by('-created_at')
    serializer = NotificationSerializer(notes, many=True)
    return Response({'notifications': serializer.data, 'count': notes.filter(is_read=False).count()})

@api_view(['PUT'])
def mark_notification_read(request, notification_id):
    note = get_object_or_404(Notification, id=notification_id, user=request.user)
    note.is_read = True
    note.save()
    return Response({'message': 'Read'})