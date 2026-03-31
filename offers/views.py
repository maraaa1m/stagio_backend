from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from datetime import date, timedelta
from .models import InternshipOffer, Skill
from .serializers import InternshipOfferSerializer, SkillSerializer
from accounts.models import Company, Student
from utils.matching import calculate_matching_score

@api_view(['POST'])
def create_offer(request):
    try:
        company = Company.objects.get(user=request.user)
    except Company.DoesNotExist:
        return Response({'error': 'Only companies can create offers'}, status=status.HTTP_403_FORBIDDEN)
    
    serializer = InternshipOfferSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(company=company)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
def get_offers(request):
    willaya = request.query_params.get('willaya', None)
    o_type = request.query_params.get('type', None)
    offers = InternshipOffer.objects.all()
    if willaya:
        offers = offers.filter(willaya=willaya)
    if o_type:
        offers = offers.filter(type=o_type)
    serializer = InternshipOfferSerializer(offers, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
def get_offer_detail(request, offer_id):
    offer = get_object_or_404(InternshipOffer, id=offer_id)
    serializer = InternshipOfferSerializer(offer)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['PUT'])
def update_offer(request, offer_id):
    try:
        company = Company.objects.get(user=request.user)
        offer = InternshipOffer.objects.get(id=offer_id, company=company)
    except (Company.DoesNotExist, InternshipOffer.DoesNotExist):
        return Response({'error': 'Offer not found or unauthorized'}, status=status.HTTP_404_NOT_FOUND)
    
    serializer = InternshipOfferSerializer(offer, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE'])
def delete_offer(request, offer_id):
    try:
        company = Company.objects.get(user=request.user)
        offer = InternshipOffer.objects.get(id=offer_id, company=company)
        offer.delete()
        return Response({'message': 'Offer deleted successfully'}, status=status.HTTP_200_OK)
    except (Company.DoesNotExist, InternshipOffer.DoesNotExist):
        return Response({'error': 'Offer not found or unauthorized'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def get_skills(request):
    skills = Skill.objects.all()
    serializer = SkillSerializer(skills, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
def get_recommended_offers(request):
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return Response({'error': 'Only students can get recommendations'}, status=status.HTTP_403_FORBIDDEN)

    offers = InternshipOffer.objects.all()
    scored_offers = []

    for offer in offers:
        score = calculate_matching_score(student, offer)
        scored_offers.append({
            'offer_id': offer.id,
            'title': offer.title,
            'company': offer.company.companyName,
            'willaya': offer.willaya,
            'type': offer.type,
            'deadline': offer.deadline,
            'matchingScore': score,
            'requiredSkills': [s.skillName for s in offer.requiredSkills.all()],
        })

    scored_offers.sort(key=lambda x: x['matchingScore'], reverse=True)
    return Response(scored_offers, status=status.HTTP_200_OK) 

@api_view(['GET'])
def get_match_score(request, offer_id):
    try:
        student = Student.objects.get(user=request.user)
        offer = InternshipOffer.objects.get(id=offer_id)
        score = calculate_matching_score(student, offer)
        return Response({'offer': offer.title, 'matchingScore': score}, status=status.HTTP_200_OK)
    except (Student.DoesNotExist, InternshipOffer.DoesNotExist):
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def get_match_report(request, offer_id):
    try:
        student = Student.objects.get(user=request.user)
        offer = InternshipOffer.objects.get(id=offer_id)
    except (Student.DoesNotExist, InternshipOffer.DoesNotExist):
        return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

    required_skills = set(offer.requiredSkills.all())
    student_skills = set(student.skills.all())
    common = required_skills & student_skills
    missing = required_skills - student_skills

    score = round((len(common) / len(required_skills)) * 100, 2) if required_skills else 100

    return Response({
        'offer': offer.title,
        'company': offer.company.companyName,
        'matchingScore': score,
        'matchedSkills': [s.skillName for s in common],
        'missingSkills': [s.skillName for s in missing],
        'message': f"Improve your profile by learning: {', '.join([s.skillName for s in missing])}" if missing else "Perfect Match!"
    }, status=status.HTTP_200_OK)

@api_view(['GET'])
def suggest_skills(request):
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

    local_offers = InternshipOffer.objects.filter(willaya=student.univWillaya)
    skill_count = {}
    for offer in local_offers:
        for skill in offer.requiredSkills.all():
            skill_count[skill.skillName] = skill_count.get(skill.skillName, 0) + 1

    student_skill_names = [s.skillName for s in student.skills.all()]
    suggestions = sorted(
        [{'skill': k, 'demand': v} for k, v in skill_count.items() if k not in student_skill_names],
        key=lambda x: x['demand'], reverse=True
    )

    return Response({'suggestions': suggestions[:5]}, status=status.HTTP_200_OK)

@api_view(['GET'])
def get_expiring_soon(request):
    today = date.today()
    in_3_days = today + timedelta(days=3)
    offers = InternshipOffer.objects.filter(deadline__gte=today, deadline__lte=in_3_days)
    
    data = [{
        'offer_id': o.id,
        'title': o.title,
        'company': o.company.companyName,
        'daysLeft': (o.deadline - today).days,
    } for o in offers]

    return Response({'offers': data}, status=status.HTTP_200_OK)