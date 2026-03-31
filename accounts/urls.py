from django.urls import path
from . import views, admin_views

urlpatterns = [
    path('register/student/', views.register_student),
    path('register/company/', views.register_company),
    path('logout/', views.logout),
    path('student/profile/', views.get_student_profile),
    path('student/update/', views.update_student_profile),
    path('student/profile/photo/', views.upload_student_photo),
    path('student/cv/upload/', views.upload_cv),
    path('company/profile/', views.get_company_profile),
    path('company/update/', views.update_company_profile),
    path('company/logo/upload/', views.upload_company_logo),
    path('admin/companies/pending/', admin_views.get_pending_companies),
    path('admin/companies/<str:company_id>/approve/', admin_views.approve_company),
    path('admin/companies/<str:company_id>/refuse/', admin_views.refuse_company),
    path('admin/statistics/', admin_views.get_statistics),
    path('admin/companies/<str:company_id>/blacklist/', admin_views.blacklist_company),
    path('admin/companies/blacklisted/', admin_views.get_blacklisted_companies),  
    path('auth/forgot-password/', views.forgot_password),
    path('auth/reset-password/', views.reset_password),
]