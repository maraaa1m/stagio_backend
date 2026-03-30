from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import InternshipOffer, Skill
from .serializers import InternshipOfferSerializer, SkillSerializer
from accounts.models import Company
from accounts.models import Student
from utils.matching import calculate_matching_score


@api_view(['POST'])
def create_offer(request):
    try:
        company = Company.objects.get(user=request.user)
    except Company.DoesNotExist:
        return Response(
            {'error': 'Only companies can create offers'},
            status=status.HTTP_403_FORBIDDEN
        )
    serializer = InternshipOfferSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(company=company)
        return Response({
            'message': 'Offer created successfully',
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_offers(request):
    willaya = request.query_params.get('willaya', None)
    type = request.query_params.get('type', None)
    offers = InternshipOffer.objects.all()
    if willaya:
        offers = offers.filter(willaya=willaya)
    if type:
        offers = offers.filter(type=type)
    serializer = InternshipOfferSerializer(offers, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_offer_detail(request, offer_id):
    try:
        offer = InternshipOffer.objects.get(id=offer_id)
        serializer = InternshipOfferSerializer(offer)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except InternshipOffer.DoesNotExist:
        return Response(
            {'error': 'Offer not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['PUT'])
def update_offer(request, offer_id):
    try:
        company = Company.objects.get(user=request.user)
        offer = InternshipOffer.objects.get(id=offer_id, company=company)
    except Company.DoesNotExist:
        return Response(
            {'error': 'Only companies can update offers'},
            status=status.HTTP_403_FORBIDDEN
        )
    except InternshipOffer.DoesNotExist:
        return Response(
            {'error': 'Offer not found or not yours'},
            status=status.HTTP_404_NOT_FOUND
        )
    serializer = InternshipOfferSerializer(
        offer, data=request.data, partial=True
    )
    if serializer.is_valid():
        serializer.save()
        return Response({
            'message': 'Offer updated successfully',
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
def delete_offer(request, offer_id):
    try:
        company = Company.objects.get(user=request.user)
        offer = InternshipOffer.objects.get(id=offer_id, company=company)
        offer.delete()
        return Response(
            {'message': 'Offer deleted successfully'},
            status=status.HTTP_200_OK
        )
    except Company.DoesNotExist:
        return Response(
            {'error': 'Only companies can delete offers'},
            status=status.HTTP_403_FORBIDDEN
        )
    except InternshipOffer.DoesNotExist:
        return Response(
            {'error': 'Offer not found or not yours'},
            status=status.HTTP_404_NOT_FOUND
        )


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
        return Response(
            {'error': 'Only students can get recommendations'},
            status=status.HTTP_403_FORBIDDEN
        )

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
    except Student.DoesNotExist:
        return Response(
            {'error': 'Only students can check match score'},
            status=status.HTTP_403_FORBIDDEN
        )
    try:
        offer = InternshipOffer.objects.get(id=offer_id)
    except InternshipOffer.DoesNotExist:
        return Response(
            {'error': 'Offer not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    score = calculate_matching_score(student, offer)

    return Response({
        'offer': offer.title,
        'matchingScore': score,
    }, status=status.HTTP_200_OK)
@api_view(['GET'])
def get_match_report(request, offer_id):
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return Response(
            {'error': 'Only students can get match report'},
            status=status.HTTP_403_FORBIDDEN
        )
    try:
        offer = InternshipOffer.objects.get(id=offer_id)
    except InternshipOffer.DoesNotExist:
        return Response(
            {'error': 'Offer not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    required_skills = list(offer.requiredSkills.all())
    student_skills = list(student.skills.all())

    common = set(required_skills) & set(student_skills)
    missing = set(required_skills) - set(student_skills)

    if len(required_skills) == 0:
        score = 100
    else:
        score = round((len(common) / len(required_skills)) * 100, 2)

    return Response({
        'offer': offer.title,
        'company': offer.company.companyName,
        'matchingScore': score,
        'yourSkills': [s.skillName for s in student_skills],
        'requiredSkills': [s.skillName for s in required_skills],
        'matchedSkills': [s.skillName for s in common],
        'missingSkills': [s.skillName for s in missing],
        'message': f"learn {', '.join([s.skillName for s in missing])} to reach the 100% match in that offer!" if missing else "You match 100% of the requirements! 🎉"
    }, status=status.HTTP_200_OK)
@api_view(['GET'])
def suggest_skills(request):
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        return Response(
            {'error': 'Only students can get skill suggestions'},
            status=status.HTTP_403_FORBIDDEN
        )


    local_offers = InternshipOffer.objects.filter(
        willaya=student.univWillaya
    )


    skill_count = {}
    for offer in local_offers:
        for skill in offer.requiredSkills.all():
            if skill.skillName in skill_count:
                skill_count[skill.skillName] += 1
            else:
                skill_count[skill.skillName] = 1


    sorted_skills = sorted(
        skill_count.items(),
        key=lambda x: x[1],
        reverse=True
    )

   
    student_skill_names = [s.skillName for s in student.skills.all()]
    suggestions = [
        {'skill': skill, 'demandCount': count}
        for skill, count in sorted_skills
        if skill not in student_skill_names
    ]

    return Response({
        'willaya': student.univWillaya,
        'suggestions': suggestions[:5],
        'message': f"Top skills demanded in {student.univWillaya} that you don't have yet"
    }, status=status.HTTP_200_OK)
from datetime import date, timedelta

@api_view(['GET'])
def get_expiring_soon(request):
    today = date.today()
    in_3_days = today + timedelta(days=3)

    offers = InternshipOffer.objects.filter(
        deadline__gte=today,
        deadline__lte=in_3_days
    )

    data = []
    for offer in offers:
        data.append({
            'offer_id': offer.id,
            'title': offer.title,
            'company': offer.company.companyName,
            'willaya': offer.willaya,
            'deadline': offer.deadline,
            'daysLeft': (offer.deadline - today).days,
        })

    return Response({
        'count': len(data),
        'offers': data
    }, status=status.HTTP_200_OK)