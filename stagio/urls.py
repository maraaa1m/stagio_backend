from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    # Changed back to standard 'admin/' for consistency
    path('admin/', admin.site.urls),

    # JWT token refresh
    path('api/auth/token/refresh/', TokenRefreshView.as_view()),

    # All API routes
    path('api/', include('accounts.urls')),
    path('api/', include('offers.urls')),
    path('api/', include('applications.urls')),
]

# Serve media (Photos, CVs, PDFs)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)