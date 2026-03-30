from django.urls import path
from . import views, admin_views

urlpatterns = [
    # Auth
    path('register/student/', views.register_student),
    path('register/company/', views.register_company),
    path('logout/', views.logout),

    # Student
    path('student/profile/', views.get_student_profile),
    path('student/update/', views.update_student_profile),

    # Company
    path('company/profile/', views.get_company_profile),
    path('company/update/', views.update_company_profile),

    # Admin
    path('admin/companies/pending/', admin_views.get_pending_companies),
    path('admin/companies/<str:company_id>/approve/', admin_views.approve_company),
    path('admin/companies/<str:company_id>/refuse/', admin_views.refuse_company),
    path('admin/statistics/', admin_views.get_statistics),
]
