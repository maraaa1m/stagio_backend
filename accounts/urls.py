from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('register/student/', views.register_student, name='register_student'),
    path('register/company/', views.register_company, name='register_company'),
    path('logout/', views.logout, name='logout'),
    
    # Student
    path('profile/', views.get_student_profile, name='student_profile'),
    path('update/', views.update_student_profile, name='update_student_profile'),
    
    # Company
    path('profile/', views.get_company_profile, name='company_profile'),
    path('update/', views.update_company_profile, name='update_company_profile'),
]