from django.urls import path
from . import views

urlpatterns = [
    path('applications/apply/', views.apply_to_offer, name='apply'),
    path('applications/<str:application_id>/', views.get_application, name='get_application'),
    path('company/applications/', views.get_company_applications, name='company_applications'),
]