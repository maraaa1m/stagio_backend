from django.urls import path
from . import views

urlpatterns = [
    path('applications/apply/', views.apply_to_offer),
    path('applications/<str:application_id>/', views.get_application),
    path('student/my-applications/', views.get_student_applications),
    path('company/applications/', views.get_company_applications),
    path('company/applications/<str:application_id>/accept/', views.accept_application),
    path('company/applications/<str:application_id>/refuse/', views.refuse_application),
    path('admin/pending-validations/', views.get_accepted_for_admin),
    path('admin/validate/<str:application_id>/', views.admin_validate_internship),
    path('notifications/', views.get_notifications),
]