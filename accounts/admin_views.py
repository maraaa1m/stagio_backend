from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from accounts.models import User, Company, Admin, Student
from applications.models import Application
from offers.models import InternshipOffer


def _require_admin(request):
    """Returns (admin, None) or (None, Response) if not admin."""
    try:
        return Admin.objects.get(user=request.user), None
    except Admin.DoesNotExist:
        return None, Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)


# ── Pending company approvals ──────────────────────────────────────────────────
@api_view(['GET'])
def get_pending_companies(request):
    admin, err = _require_admin(request)
    if err:
        return err

    companies = Company.objects.filter(isApproved=False, isBlacklisted=False).select_related('user')
    data = [
        {
            'id':          c.id,
            'companyName': c.companyName,
            'email':       c.user.email,
            'location':    c.location,
            'description': c.description or '',
            'website':     c.website or '',
            'phoneNumber': c.phoneNumber or '',
        }
        for c in companies
    ]
    return Response(data, status=status.HTTP_200_OK)


# ── All approved companies ────────────────────────────────────────────────────
@api_view(['GET'])
def get_all_companies(request):
    admin, err = _require_admin(request)
    if err:
        return err

    companies = Company.objects.filter(isApproved=True).select_related('user')
    data = [
        {
            'id':              c.id,
            'companyName':     c.companyName,
            'email':           c.user.email,
            'location':        c.location,
            'website':         c.website or '',
            'phoneNumber':     c.phoneNumber or '',
            'isBlacklisted':   c.isBlacklisted,
            'totalOffers':     c.offers.count(),
        }
        for c in companies
    ]
    return Response(data, status=status.HTTP_200_OK)


# ── Approve company ────────────────────────────────────────────────────────────
@api_view(['PUT'])
def approve_company(request, company_id):
    admin, err = _require_admin(request)
    if err:
        return err

    try:
        company            = Company.objects.get(id=company_id)
        company.isApproved = True
        company.save()
        return Response(
            {'message': f'{company.companyName} approved successfully'},
            status=status.HTTP_200_OK,
        )
    except Company.DoesNotExist:
        return Response({'error': 'Company not found'}, status=status.HTTP_404_NOT_FOUND)


# ── Refuse (delete) company ────────────────────────────────────────────────────
@api_view(['PUT'])
def refuse_company(request, company_id):
    admin, err = _require_admin(request)
    if err:
        return err

    try:
        company = Company.objects.get(id=company_id)
        company.delete()
        return Response(
            {'message': 'Company refused and removed from system'},
            status=status.HTTP_200_OK,
        )
    except Company.DoesNotExist:
        return Response({'error': 'Company not found'}, status=status.HTTP_404_NOT_FOUND)


# ── Blacklist company ──────────────────────────────────────────────────────────
@api_view(['PUT'])
def blacklist_company(request, company_id):
    admin, err = _require_admin(request)
    if err:
        return err

    try:
        company                = Company.objects.get(id=company_id)
        company.isBlacklisted  = True
        company.isApproved     = False
        company.save()
        return Response(
            {'message': f'{company.companyName} has been blacklisted'},
            status=status.HTTP_200_OK,
        )
    except Company.DoesNotExist:
        return Response({'error': 'Company not found'}, status=status.HTTP_404_NOT_FOUND)


# ── Blacklisted companies list ────────────────────────────────────────────────
@api_view(['GET'])
def get_blacklisted_companies(request):
    admin, err = _require_admin(request)
    if err:
        return err

    companies = Company.objects.filter(isBlacklisted=True).select_related('user')
    data = [
        {
            'id':          c.id,
            'companyName': c.companyName,
            'email':       c.user.email,
            'location':    c.location,
        }
        for c in companies
    ]
    return Response(data, status=status.HTTP_200_OK)


# ── Statistics ────────────────────────────────────────────────────────────────
@api_view(['GET'])
def get_statistics(request):
    admin, err = _require_admin(request)
    if err:
        return err

    total_students = Student.objects.count()
    placed = (
        Application.objects
        .filter(applicationStatus='VALIDATED')
        .values('student')
        .distinct()
        .count()
    )

    data = {
        'total_students':       total_students,
        'placed_students':      placed,
        'unplaced_students':    total_students - placed,
        'total_companies':      Company.objects.filter(isApproved=True).count(),
        'pending_companies':    Company.objects.filter(isApproved=False, isBlacklisted=False).count(),
        'total_offers':         InternshipOffer.objects.count(),
        'total_applications':   Application.objects.count(),
        'pending_applications': Application.objects.filter(applicationStatus='PENDING').count(),
        'accepted_applications':Application.objects.filter(applicationStatus='ACCEPTED').count(),
        'validated_applications':Application.objects.filter(applicationStatus='VALIDATED').count(),
        'refused_applications': Application.objects.filter(applicationStatus='REFUSED').count(),
    }
    return Response(data, status=status.HTTP_200_OK)


# ── All validated agreements (for agreements page) ────────────────────────────
@api_view(['GET'])
def get_all_agreements(request):
    admin, err = _require_admin(request)
    if err:
        return err

    from applications.models import Agreement
    agreements = (
        Agreement.objects
        .filter(status='VALIDATED')
        .select_related(
            'internship__application__student',
            'internship__application__offer__company',
            'admin',
        )
    )
    data = []
    for ag in agreements:
        app = ag.internship.application
        data.append({
            'id':           ag.id,
            'student':      f"{app.student.firstName} {app.student.lastName}",
            'company':      app.offer.company.companyName,
            'offer':        app.offer.title,
            'generatedOn':  str(ag.generationDate),
            'pdfUrl':       ag.pdfUrl.url if ag.pdfUrl else None,
        })
    return Response(data, status=status.HTTP_200_OK)