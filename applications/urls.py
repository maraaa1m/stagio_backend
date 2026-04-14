from django.urls import path
from . import views

urlpatterns = [
    # ── Applications ───────────────────────────────────────────────────────────
    path('applications/apply/',                              views.apply_to_offer),
    path('applications/<int:application_id>/',               views.get_application),

    # Student views — two aliases so both URL patterns work
    path('student/applications/',                            views.get_student_applications),
    path('student/my-applications/',                         views.get_student_applications),

    # Company views
    path('company/applications/',                            views.get_company_applications),
    path('company/applications/<int:application_id>/accept/', views.accept_application),
    path('company/applications/<int:application_id>/refuse/', views.refuse_application),

    # Admin views
    path('admin/pending-validations/',                       views.get_accepted_for_admin),
    path('admin/validate/<int:application_id>/',             views.admin_validate_internship),

    # ── Notifications ──────────────────────────────────────────────────────────
    path('notifications/',                                   views.get_notifications),
    path('student/notifications/',                           views.get_notifications),  # alias
    path('notifications/<int:notification_id>/read/',        views.mark_notification_read),
    path('notifications/read-all/',                          views.mark_all_notifications_read),
]