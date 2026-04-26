from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.conf import settings
from datetime import date # Added for temporal check

from .models import Application, Internship, Agreement, Certificate, Notification
from .serializers import NotificationSerializer
from accounts.models import Student, Company, Admin
from offers.models import InternshipOffer
from utils.matching import calculate_matching_score
from utils.pdf_generator import generate_agreement_pdf, generate_certificate_pdf # Added Certificate import

# ── STUDENT: APPLY TO AN OFFER ───────────────────────────────────────────────
@api_view(['POST'])
def apply_to_offer(request):
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return Response({'error': 'Only students can apply.'}, status=status.HTTP_403_FORBIDDEN)

    offer_id = request.data.get('offer_id')
    if not offer_id:
        return Response({'error': 'offer_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

    offer = get_object_or_404(InternshipOffer, id=offer_id)

    # RECRUITMENT GUARD: Check if offer is active and has spots
    if not offer.is_active or offer.remainingSpots <= 0:
        return Response({'error': 'This offer is no longer accepting applications.'}, status=400)

    if Application.objects.filter(student=student, offer=offer).exists():
        return Response(
            {'error': 'You have already applied to this offer.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    score = calculate_matching_score(student, offer)
    Application.objects.create(student=student, offer=offer, matchingScore=score)

    return Response(
        {'message': 'Application submitted successfully.', 'matchingScore': score, 'status': 'PENDING'},
        status=status.HTTP_201_CREATED,
    )


# ── STUDENT: LIST APPLICATIONS (WITH FULL DOC LINKS) ─────────────────────────
@api_view(['GET'])
def get_student_applications(request):
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return Response({'error': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)

    apps = Application.objects.filter(student=student).select_related(
        'offer', 'offer__company'
    ).order_by('-applicationDate')

    data = []
    for a in apps:
        # PULLING BOTH START AND END DOCUMENTS
        pdf_agreement = None
        pdf_certificate = None
        
        if hasattr(a, 'internship'):
            # Check for Agreement (Start of Internship)
            if hasattr(a.internship, 'agreement') and a.internship.agreement.pdfUrl:
                pdf_agreement = request.build_absolute_uri(a.internship.agreement.pdfUrl.url)
            
            # Check for Certificate (End of Internship)
            if hasattr(a.internship, 'certificate') and a.internship.certificate.pdfUrl:
                pdf_certificate = request.build_absolute_uri(a.internship.certificate.pdfUrl.url)

        data.append({
            'id':             a.id,
            'offer_id':       a.offer.id,
            'offerTitle':     a.offer.title,
            'company':        a.offer.company.companyName,
            'status':         a.applicationStatus, # PENDING, ACCEPTED, VALIDATED
            'internshipStatus': a.internship.status if hasattr(a, 'internship') else None, # ONGOING, PENDING_CERT, COMPLETED
            'matchingScore':  a.matchingScore,
            'appliedAt':      str(a.applicationDate),
            'pdfUrl':         pdf_agreement, # For backward compatibility
            'pdfAgreement':   pdf_agreement,
            'pdfCertificate': pdf_certificate,
            'refusalReason':  getattr(a, 'refusal_reason', None),
        })
    return Response(data, status=status.HTTP_200_OK)


# ── COMPANY: LIST APPLICANTS (WITH METADATA) ─────────────────────────────────
@api_view(['GET'])
def get_company_applications(request):
    try:
        company = Company.objects.get(user=request.user)
    except Company.DoesNotExist:
        return Response({'error': 'Only companies can view applications.'}, status=status.HTTP_403_FORBIDDEN)

    applications = (
        Application.objects
        .filter(offer__company=company)
        .select_related('offer', 'student', 'student__user')
        .prefetch_related('student__skills')
        .order_by('-matchingScore')
    )

    data = []
    for app in applications:
        # Evidence-Based Decisions: Pulling CV and Links
        cv_url = request.build_absolute_uri(app.student.cvFile.url) if app.student.cvFile else None
        
        data.append({
            'id':              app.id,
            'status':          app.applicationStatus,
            'internshipStatus': app.internship.status if hasattr(app, 'internship') else None,
            'internshipId':    app.internship.id if hasattr(app, 'internship') else None,
            'matchingScore':   app.matchingScore,
            'applicationDate': str(app.applicationDate),
            'offer_title':     app.offer.title,
            'student': {
                'firstName':     app.student.firstName,
                'lastName':      app.student.lastName,
                'email':         app.student.user.email,
                'cv':            cv_url,
                'githubLink':    app.student.githubLink or '',
                'portfolioLink': app.student.portfolioLink or '',
                'skills':        [s.skillName for s in app.student.skills.all()],
            },
        })
    return Response(data, status=status.HTTP_200_OK)


# ── COMPANY: ACCEPT/REFUSE ───────────────────────────────────────────────────
@api_view(['PUT'])
def accept_application(request, application_id):
    try:
        company = Company.objects.get(user=request.user)
        app     = Application.objects.get(id=application_id, offer__company=company)
        if app.applicationStatus != 'PENDING':
            return Response({'error': 'Already processed.'}, status=400)
        app.applicationStatus = 'ACCEPTED'
        app.save()
        Notification.objects.create(user=app.student.user, message=f"Accepted by {company.companyName}.")
        return Response({'message': 'Accepted.', 'status': 'ACCEPTED'})
    except:
        return Response(status=404)

@api_view(['PUT'])
def refuse_application(request, application_id):
    try:
        company = Company.objects.get(user=request.user)
        app     = Application.objects.get(id=application_id, offer__company=company)
        reason = request.data.get('reason', '').strip() or 'No reason provided.'
        app.applicationStatus = 'REFUSED'
        if hasattr(app, 'refusal_reason'): app.refusal_reason = reason
        app.save()
        Notification.objects.create(user=app.student.user, message=f"Refused by {company.companyName}. Reason: {reason}")
        return Response({'message': 'Refused.'})
    except:
        return Response(status=404)


# ── NEW: COMPANY FINALIZATION (MARK AS ENDED) ────────────────────────────────
@api_view(['POST'])
def company_mark_internship_ended(request, internship_id):
    """
    Logic: Company validates that the student successfully finished their duties.
    Status moves: ONGOING -> PENDING_CERT.
    """
    try:
        company = Company.objects.get(user=request.user)
        internship = get_object_or_404(Internship, id=internship_id, application__offer__company=company)
        
        # Security: Only allow finalizing if work period has passed
        if date.today() < internship.endDate:
             return Response({'error': 'Internship period is not finished yet.'}, status=400)

        internship.status = Internship.PENDING_CERT
        internship.save()

        # Notify Admin to generate the final certificate
        student_dept = internship.application.student.department
        dept_admins = Admin.objects.filter(department=student_dept)
        for admin in dept_admins:
            Notification.objects.create(user=admin.user, message=f"Completion Approval required for {internship.application.student.firstName}")

        return Response({'message': 'Internship marked as finished. Sent to Admin for certification.'})
    except Company.DoesNotExist:
        return Response(status=403)


# ── ADMIN: PENDING VALIDATIONS (HIERARCHICAL) ────────────────────────────────
@api_view(['GET'])
def get_accepted_for_admin(request):
    try:
        admin = Admin.objects.get(user=request.user)
        qs = Application.objects.filter(applicationStatus='ACCEPTED').select_related('student', 'offer', 'offer__company')

        # Logic: Superadmin sees everything. Dept Head sees only their students.
        if not admin.is_superadmin:
            qs = qs.filter(student__department=admin.department)

        data = []
        for a in qs:
            data.append({
                'id':      a.id,
                'student': f"{a.student.firstName} {a.student.lastName}",
                'dept':    a.student.department.name if a.student.department else 'N/A',
                'company': a.offer.company.companyName,
                'offer':   a.offer.title,
                'score':   a.matchingScore
            })
        return Response(data)
    except Admin.DoesNotExist:
        return Response({'error': 'Admin access required.'}, status=403)


# ── ADMIN: MASTER BUTTON (VALIDATE AGREEMENT) ────────────────────────────────
@api_view(['POST'])
def admin_validate_internship(request, application_id):
    try:
        admin = Admin.objects.get(user=request.user)
        # Security: Ensure Admin has jurisdiction over the student
        query_params = {'id': application_id, 'applicationStatus': 'ACCEPTED'}
        if not admin.is_superadmin:
            query_params['student__department'] = admin.department
            
        app = get_object_or_404(Application, **query_params)

        # 1. Capacity Check
        if not app.offer.is_active or app.offer.remainingSpots <= 0:
            return Response({'error': 'Offer capacity reached.'}, status=400)

        # 2. Orchestration: Create Internship + PDF
        internship, _ = Internship.objects.get_or_create(
            application=app,
            defaults={
                'startDate': app.offer.internshipStartDate,
                'endDate': app.offer.internshipEndDate,
                'topic': app.offer.title,
                'supervisorName': f"Admin {admin.lastName}",
                'status': Internship.ONGOING
            }
        )

        pdf_file = generate_agreement_pdf(app, admin)
        Agreement.objects.update_or_create(internship=internship, defaults={'admin': admin, 'pdfUrl': pdf_file})
        
        app.applicationStatus = 'VALIDATED'
        app.save()

        Notification.objects.create(user=app.student.user, message="Internship Validated! Agreement generated.")
        return Response({'message': 'Validated & PDF Generated'}, status=201)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


# ── ADMIN: MASTER BUTTON (ISSUE CERTIFICATE) ────────────────────────────────
@api_view(['POST'])
def admin_issue_certificate(request, internship_id):
    """
    Logic: Admin signs the work completion.
    Generates Hiba's Landscape Certificate.
    Status moves: PENDING_CERT -> COMPLETED.
    """
    try:
        admin = Admin.objects.get(user=request.user)
        # Security: Scoped check
        query_params = {'id': internship_id, 'status': Internship.PENDING_CERT}
        if not admin.is_superadmin:
            query_params['application__student__department'] = admin.department
        
        internship = get_object_or_404(Internship, **query_params)

        # 1. Generate the Diploma
        pdf_file = generate_certificate_pdf(internship, admin)

        # 2. Create the Certificate record
        Certificate.objects.create(
            internship=internship,
            admin=admin,
            pdfUrl=pdf_file
        )

        # 3. Close the loop
        internship.status = Internship.COMPLETED
        internship.save()

        Notification.objects.create(user=internship.application.student.user, message="Final Certificate Issued! Download it now.")
        return Response({'message': 'Certificate officially issued.'}, status=201)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


# ── NOTIFICATIONS ────────────────────────────────────────────────────────────
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