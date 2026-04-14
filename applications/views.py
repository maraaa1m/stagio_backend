from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import Application, Internship, Agreement, Notification
from .serializers import NotificationSerializer
from accounts.models import Student, Company, Admin
from offers.models import InternshipOffer
from utils.matching import calculate_matching_score
from utils.pdf_generator import generate_agreement_pdf


# ── Student: apply to an offer ─────────────────────────────────────────────────
@api_view(['POST'])
def apply_to_offer(request):
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return Response({'error': 'Only students can apply'}, status=status.HTTP_403_FORBIDDEN)

    offer_id = request.data.get('offer_id')
    if not offer_id:
        return Response({'error': 'offer_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    offer = get_object_or_404(InternshipOffer, id=offer_id)

    if Application.objects.filter(student=student, offer=offer).exists():
        return Response(
            {'error': 'You have already applied to this offer'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    score = calculate_matching_score(student, offer)
    Application.objects.create(student=student, offer=offer, matchingScore=score)

    return Response(
        {'message': 'Application submitted successfully', 'matchingScore': score, 'status': 'PENDING'},
        status=status.HTTP_201_CREATED,
    )


# ── Student: list own applications ────────────────────────────────────────────
@api_view(['GET'])
def get_student_applications(request):
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return Response({'error': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)

    apps = Application.objects.filter(student=student).select_related(
        'offer', 'offer__company'
    ).order_by('-applicationDate')

    data = []
    for a in apps:
        pdf_url = None
        if (
            hasattr(a, 'internship')
            and hasattr(a.internship, 'agreement')
            and a.internship.agreement.pdfUrl
        ):
            pdf_url = a.internship.agreement.pdfUrl.url

        data.append({
            'id':             a.id,
            'offer_id':       a.offer.id,        # needed by OfferDetail "already applied" check
            'offerTitle':     a.offer.title,
            'offer_title':    a.offer.title,      # alias for safety
            'company':        a.offer.company.companyName,
            'company_name':   a.offer.company.companyName,
            'status':         a.applicationStatus,
            'matchingScore':  a.matchingScore,
            'matching_score': a.matchingScore,
            'appliedAt':      str(a.applicationDate),
            'applied_date':   str(a.applicationDate),  # alias
            'pdfUrl':         pdf_url,
            'pdf_url':        pdf_url,
            'refusalReason':  getattr(a, 'refusal_reason', None),
            'refusal_reason': getattr(a, 'refusal_reason', None),
        })
    return Response(data, status=status.HTTP_200_OK)


# ── Student: single application detail ────────────────────────────────────────
@api_view(['GET'])
def get_application(request, application_id):
    try:
        application = Application.objects.get(id=application_id, student__user=request.user)
    except Application.DoesNotExist:
        return Response({'error': 'Application not found'}, status=status.HTTP_404_NOT_FOUND)

    pdf_url = None
    if (
        hasattr(application, 'internship')
        and hasattr(application.internship, 'agreement')
        and application.internship.agreement.pdfUrl
    ):
        pdf_url = application.internship.agreement.pdfUrl.url

    return Response({
        'id':            application.id,
        'offer_id':      application.offer.id,
        'offerTitle':    application.offer.title,
        'company':       application.offer.company.companyName,
        'status':        application.applicationStatus,
        'matchingScore': application.matchingScore,
        'appliedAt':     str(application.applicationDate),
        'pdfUrl':        pdf_url,
    }, status=status.HTTP_200_OK)


# ── Company: list all applications for their offers ───────────────────────────
@api_view(['GET'])
def get_company_applications(request):
    try:
        company = Company.objects.get(user=request.user)
    except Company.DoesNotExist:
        return Response({'error': 'Only companies can view applications'}, status=status.HTTP_403_FORBIDDEN)

    applications = (
        Application.objects
        .filter(offer__company=company)
        .select_related('offer', 'student', 'student__user')
        .prefetch_related('student__skills')
        .order_by('-matchingScore')
    )

    data = []
    for app in applications:
        data.append({
            'id':           app.id,
            'status':       app.applicationStatus,
            'matchingScore': app.matchingScore,
            'matching_score': app.matchingScore,
            'applicationDate': str(app.applicationDate),
            'offer_title':  app.offer.title,
            'offer':        app.offer.title,
            'student': {
                'firstName':     app.student.firstName,
                'lastName':      app.student.lastName,
                'email':         app.student.user.email,
                'skills':        [s.skillName for s in app.student.skills.all()],
                'githubLink':    app.student.githubLink or '',
                'portfolioLink': app.student.portfolioLink or '',
            },
        })
    return Response(data, status=status.HTTP_200_OK)


# ── Company: accept application ────────────────────────────────────────────────
@api_view(['PUT'])
def accept_application(request, application_id):
    try:
        company = Company.objects.get(user=request.user)
        app     = Application.objects.get(id=application_id, offer__company=company)
    except (Company.DoesNotExist, Application.DoesNotExist):
        return Response({'error': 'Not found or unauthorized'}, status=status.HTTP_404_NOT_FOUND)

    if app.applicationStatus != 'PENDING':
        return Response({'error': 'Application already processed'}, status=status.HTTP_400_BAD_REQUEST)

    app.applicationStatus = 'ACCEPTED'
    app.save()

    Notification.objects.create(
        user=app.student.user,
        message=(
            f"Congratulations! Your application for '{app.offer.title}' "
            f"has been ACCEPTED by {company.companyName}. "
            f"The university admin will validate it shortly."
        ),
    )
    return Response(
        {'message': 'Application accepted', 'status': 'ACCEPTED'},
        status=status.HTTP_200_OK,
    )


# ── Company: refuse application ────────────────────────────────────────────────
@api_view(['PUT'])
def refuse_application(request, application_id):
    try:
        company = Company.objects.get(user=request.user)
        app     = Application.objects.get(id=application_id, offer__company=company)
    except (Company.DoesNotExist, Application.DoesNotExist):
        return Response({'error': 'Not found or unauthorized'}, status=status.HTTP_404_NOT_FOUND)

    if app.applicationStatus != 'PENDING':
        return Response({'error': 'Application already processed'}, status=status.HTTP_400_BAD_REQUEST)

    reason = request.data.get('reason', '').strip() or 'No reason provided'

    # Persist the refusal reason if the model has that field
    app.applicationStatus = 'REFUSED'
    if hasattr(app, 'refusal_reason'):
        app.refusal_reason = reason
    app.save()

    Notification.objects.create(
        user=app.student.user,
        message=(
            f"Your application for '{app.offer.title}' was not accepted. "
            f"Reason: {reason}"
        ),
    )
    return Response(
        {'message': 'Application refused', 'status': 'REFUSED'},
        status=status.HTTP_200_OK,
    )


# ── Admin: list ACCEPTED applications awaiting validation ─────────────────────
@api_view(['GET'])
def get_accepted_for_admin(request):
    try:
        Admin.objects.get(user=request.user)
    except Admin.DoesNotExist:
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)

    apps = (
        Application.objects
        .filter(applicationStatus='ACCEPTED')
        .select_related('student', 'offer', 'offer__company')
    )
    data = [
        {
            'id':      a.id,
            'student': f"{a.student.firstName} {a.student.lastName}",
            'company': a.offer.company.companyName,
            'offer':   a.offer.title,
        }
        for a in apps
    ]
    return Response(data, status=status.HTTP_200_OK)


# ── Admin: validate internship & generate PDF ─────────────────────────────────
@api_view(['POST'])
def admin_validate_internship(request, application_id):
    try:
        admin = Admin.objects.get(user=request.user)
    except Admin.DoesNotExist:
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)

    app = get_object_or_404(Application, id=application_id, applicationStatus='ACCEPTED')

    try:
        internship, _ = Internship.objects.get_or_create(
            application=app,
            defaults={
                'startDate':      app.offer.startingDay,
                'endDate':        app.offer.deadline,
                'topic':          app.offer.title,
                'supervisorName': f"{admin.firstName} {admin.lastName}",
            },
        )

        pdf_file = generate_agreement_pdf(app, admin)

        Agreement.objects.update_or_create(
            internship=internship,
            defaults={'admin': admin, 'pdfUrl': pdf_file, 'status': 'VALIDATED'},
        )

        app.applicationStatus = 'VALIDATED'
        app.save()

        Notification.objects.create(
            user=app.student.user,
            message=(
                f"Your internship at {app.offer.company.companyName} has been officially VALIDATED. "
                f"Your internship agreement (Convention de Stage) is ready to download."
            ),
        )
        return Response(
            {'message': 'Internship validated and agreement PDF generated!'},
            status=status.HTTP_201_CREATED,
        )
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ── Notifications ──────────────────────────────────────────────────────────────
@api_view(['GET'])
def get_notifications(request):
    notes = (
        Notification.objects
        .filter(user=request.user)
        .order_by('-created_at')
    )
    serializer = NotificationSerializer(notes, many=True)
    # Also return unread count for the bell badge
    unread = notes.filter(is_read=False).count()
    return Response({'notifications': serializer.data, 'count': unread}, status=status.HTTP_200_OK)


@api_view(['PUT'])
def mark_notification_read(request, notification_id):
    try:
        note = Notification.objects.get(id=notification_id, user=request.user)
        note.is_read = True
        note.save()
        return Response({'message': 'Marked as read'}, status=status.HTTP_200_OK)
    except Notification.DoesNotExist:
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['PUT'])
def mark_all_notifications_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return Response({'message': 'All notifications marked as read'}, status=status.HTTP_200_OK)