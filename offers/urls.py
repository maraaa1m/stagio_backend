from django.urls import path
from . import views

urlpatterns = [
    path('offers/', views.get_offers, name='get_offers'),
    path('offers/create/', views.create_offer, name='create_offer'),
    path('offers/<str:offer_id>/', views.get_offer_detail, name='get_offer_detail'),
    path('offers/<str:offer_id>/update/', views.update_offer, name='update_offer'),
    path('offers/<str:offer_id>/delete/', views.delete_offer, name='delete_offer'),
    path('skills/', views.get_skills, name='get_skills'),
]