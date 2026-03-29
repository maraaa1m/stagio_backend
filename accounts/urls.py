from django.urls import path
from . import views

urlpatterns = [
    path('register/student/', views.register_student, name='register_student'),
    path('register/company/', views.register_company, name='register_company'),
    path('student/profile/', views.get_student_profile, name='student_profile'),
    path('logout/', views.logout, name='logout'),
]