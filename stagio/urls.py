from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('admin/', admin.site.urls),

    # JWT Auth
    path('api/auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Accounts (auth + student + company)
    path('api/auth/', include('accounts.urls')),
    path('api/student/', include('accounts.urls')),
    path('api/company/', include('accounts.urls')),

    # Offers
    path('api/', include('offers.urls')),

    # Applications
    path('api/', include('applications.urls')),
]

