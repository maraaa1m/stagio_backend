from django.urls import path
from . import views

urlpatterns = [
    # -- Student Applications --
    path('applications/apply/', views.apply_to_offer),
    path('student/my-applications/', views.get_student_applications),
    path('student/applications/', views.get_student_applications),

    # -- Company Management --
    path('company/applications/', views.get_company_applications),
    path('company/applications/<int:application_id>/accept/', views.accept_application),
    path('company/applications/<int:application_id>/refuse/', views.refuse_application),

    # -- Admin Academic Validation (Dept Head / Dean) --
    path('admin/pending-validations/', views.get_accepted_for_admin),
    path('admin/applications/', views.get_accepted_for_admin), # FIXED: Added alias for the Frontend 404
    path('admin/validate/<int:application_id>/', views.admin_validate_internship),

    # -- Notifications System --
    path('notifications/', views.get_notifications),
    path('student/notifications/', views.get_notifications),
]