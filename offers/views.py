from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import InternshipOffer, Skill
from .serializers import InternshipOfferSerializer, SkillSerializer
from accounts.models import Company


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