from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from datetime import date, timedelta

from .models import InternshipOffer, Skill
from .serializers import InternshipOfferSerializer, SkillSerializer
from accounts.models import Company, Student
from utils.matching import calculate_matching_score


# ── Company: create offer ──────────────────────────────────────────────────────
@api_view(['POST'])
def create_offer(request):
    try:
        company = Company.objects.get(user=request.user)
    except Company.DoesNotExist:
        return Response({'error': 'Only companies can create offers'}, status=status.HTTP_403_FORBIDDEN)

    if not company.isApproved:
        return Response(
            {'error': 'Your company account must be approved before posting offers'},
            status=status.HTTP_403_FORBIDDEN,
        )

    serializer = InternshipOfferSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(company=company)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ── Company: list OWN offers (GET /api/offers/) ────────────────────────────────
# Public access is via /api/offers/recommended/ (student-facing).
# This endpoint is company-facing: returns only offers belonging to the requester.
@api_view(['GET'])
def get_offers(request):
    try:
        company = Company.objects.get(user=request.user)
        offers  = InternshipOffer.objects.filter(company=company)
    except Company.DoesNotExist:
        # Fallback: non-company callers (e.g. admin) get everything
        offers = InternshipOffer.objects.all()

    serializer = InternshipOfferSerializer(offers, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


# ── Offer detail (public) ──────────────────────────────────────────────────────
@api_view(['GET'])
def get_offer_detail(request, offer_id):
    offer      = get_object_or_404(InternshipOffer, id=offer_id)
    serializer = InternshipOfferSerializer(offer)
    data       = serializer.data

    # Normalise field names so frontend mapping always works
    data['wilaya']      = offer.willaya
    data['company']     = offer.company.companyName
    data['company_name']= offer.company.companyName
    data['skills']      = [s.skillName for s in offer.requiredSkills.all()]
    data['required_skills'] = data['skills']
    data['startDate']   = str(offer.startingDay)
    data['start_date']  = str(offer.startingDay)
    return Response(data, status=status.HTTP_200_OK)


# ── Company: update offer ──────────────────────────────────────────────────────
@api_view(['PUT'])
def update_offer(request, offer_id):
    try:
        company = Company.objects.get(user=request.user)
        offer   = InternshipOffer.objects.get(id=offer_id, company=company)
    except (Company.DoesNotExist, InternshipOffer.DoesNotExist):
        return Response({'error': 'Offer not found or unauthorized'}, status=status.HTTP_404_NOT_FOUND)

    serializer = InternshipOfferSerializer(offer, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ── Company: delete offer ──────────────────────────────────────────────────────
@api_view(['DELETE'])
def delete_offer(request, offer_id):
    try:
        company = Company.objects.get(user=request.user)
        offer   = InternshipOffer.objects.get(id=offer_id, company=company)
        offer.delete()
        return Response({'message': 'Offer deleted successfully'}, status=status.HTTP_200_OK)
    except (Company.DoesNotExist, InternshipOffer.DoesNotExist):
        return Response({'error': 'Offer not found or unauthorized'}, status=status.HTTP_404_NOT_FOUND)


# ── Skills ─────────────────────────────────────────────────────────────────────
@api_view(['GET'])
def get_skills(request):
    skills     = Skill.objects.all().order_by('skillName')
    serializer = SkillSerializer(skills, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


# ── Student: recommended offers (scored + sorted) ─────────────────────────────
@api_view(['GET'])
def get_recommended_offers(request):
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return Response({'error': 'Only students can get recommendations'}, status=status.HTTP_403_FORBIDDEN)

    offers        = InternshipOffer.objects.select_related('company').prefetch_related('requiredSkills')
    scored_offers = []

    for offer in offers:
        score = calculate_matching_score(student, offer)
        scored_offers.append({
            'offer_id':      offer.id,
            'id':            offer.id,
            'title':         offer.title,
            'company':       offer.company.companyName,
            'company_name':  offer.company.companyName,
            'willaya':       offer.willaya,
            'wilaya':        offer.willaya,
            'type':          offer.type,
            'deadline':      str(offer.deadline),
            'matchingScore': score,
            'matching_score': score,
            'requiredSkills': [s.skillName for s in offer.requiredSkills.all()],
            'required_skills': [s.skillName for s in offer.requiredSkills.all()],
        })

    scored_offers.sort(key=lambda x: x['matchingScore'], reverse=True)
    return Response(scored_offers, status=status.HTTP_200_OK)


# ── Student: match report for a specific offer ────────────────────────────────
@api_view(['GET'])
def get_match_report(request, offer_id):
    try:
        student = Student.objects.get(user=request.user)
        offer   = InternshipOffer.objects.get(id=offer_id)
    except (Student.DoesNotExist, InternshipOffer.DoesNotExist):
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    required = set(offer.requiredSkills.all())
    owned    = set(student.skills.all())
    common   = required & owned
    missing  = required - owned

    score = round((len(common) / len(required)) * 100, 2) if required else 100

    return Response({
        'offer':          offer.title,
        'company':        offer.company.companyName,
        'matchingScore':  score,
        'matching_score': score,
        'matchedSkills':  [s.skillName for s in common],
        'matched_skills': [s.skillName for s in common],
        'missingSkills':  [s.skillName for s in missing],
        'missing_skills': [s.skillName for s in missing],
        'message':        (
            f"Learn {list(missing)[0].skillName} to reach 100% match!" if missing else "Perfect match!"
        ),
    }, status=status.HTTP_200_OK)


# ── Student: match score only ─────────────────────────────────────────────────
@api_view(['GET'])
def get_match_score(request, offer_id):
    try:
        student = Student.objects.get(user=request.user)
        offer   = InternshipOffer.objects.get(id=offer_id)
        score   = calculate_matching_score(student, offer)
        return Response({'offer': offer.title, 'matchingScore': score}, status=status.HTTP_200_OK)
    except (Student.DoesNotExist, InternshipOffer.DoesNotExist):
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)


# ── Student: expiring soon (≤ 7 days) ────────────────────────────────────────
@api_view(['GET'])
def get_expiring_soon(request):
    today    = date.today()
    in_7days = today + timedelta(days=7)
    offers   = (
        InternshipOffer.objects
        .filter(deadline__gte=today, deadline__lte=in_7days)
        .select_related('company')
    )
    data = [
        {
            'offer_id':  o.id,
            'id':        o.id,
            'title':     o.title,
            'company':   o.company.companyName,
            'daysLeft':  (o.deadline - today).days,
            'days_left': (o.deadline - today).days,
        }
        for o in offers
    ]
    return Response(data, status=status.HTTP_200_OK)


# ── Student: skill suggestions based on local demand ─────────────────────────
@api_view(['GET'])
def suggest_skills(request):
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

    local_offers  = InternshipOffer.objects.filter(willaya=student.univWillaya)
    skill_count   = {}
    for offer in local_offers:
        for skill in offer.requiredSkills.all():
            skill_count[skill.skillName] = skill_count.get(skill.skillName, 0) + 1

    owned_names = {s.skillName for s in student.skills.all()}
    suggestions = sorted(
        [{'skill': k, 'demand': v} for k, v in skill_count.items() if k not in owned_names],
        key=lambda x: x['demand'],
        reverse=True,
    )
    return Response({'suggestions': suggestions[:5]}, status=status.HTTP_200_OK)