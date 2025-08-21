from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.workout_view, name='home'),
    path('register/', views.register_view, name='register'),
    path('log-workout/', views.log_workout_api, name='log_workout_api'),
    path('log-goal/', views.log_goal_api, name='log_goal_api'),
    path('goals/', views.goal_view, name='goals'),
    path('weight/', views.weight_tracker_view, name='weight_tracker'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('dashboard-data/', views.dashboard_data_api, name='dashboard_data'),
    path('log-weight/', views.log_weight_api, name='log_weight_api'),
    path('weight-history/', views.log_weight_api, name='weight_history'),
    path('logout/', views.logout_view, name='logout'),
    
    # New feature URLs
    path('calendar/', views.calendar_view, name='calendar'),
    path('scheduled-workout-api/', views.scheduled_workout_api, name='scheduled_workout_api'),
    path('scheduled-workout-api/<int:workout_id>/', views.scheduled_workout_detail_api, name='scheduled_workout_detail_api'),
    path('personal-bests/', views.personal_bests_view, name='personal_bests'),
    path('personal-best-api/', views.personal_best_api, name='personal_best_api'),
    path('personal-best-api/<int:pr_id>/', views.personal_best_detail_api, name='personal_best_detail_api'),
    path('journal/', views.journal_view, name='journal'),
    path('journal-api/', views.journal_api, name='journal_api'),
    path('journal-api/<int:entry_id>/', views.journal_entry_api, name='journal_entry_api'),
    path('journal-api/stats/', views.journal_stats_api, name='journal_stats_api'),
    
    # Rest Timer feature
    path('rest-timer/', views.rest_timer_view, name='rest_timer'),
    path('rest-timer-api/', views.rest_timer_api, name='rest_timer_api'),
    path('rest-timer-api/<int:timer_id>/', views.rest_timer_detail_api, name='rest_timer_detail_api'),
    
    # Progress Photos feature
    path('progress-photos/', views.progress_photos_view, name='progress_photos'),
    path('progress-photo-api/', views.progress_photo_api, name='progress_photo_api'),
    path('progress-photo-api/<int:photo_id>/', views.progress_photo_detail_api, name='progress_photo_detail_api'),
    
    # Export Progress feature
    path('export-progress/', views.export_progress_view, name='export_progress'),
    path('export-workout-csv/', views.export_workout_csv, name='export_workout_csv'),
    path('export-weight-csv/', views.export_weight_csv, name='export_weight_csv'),
    path('export-workout-pdf/', views.export_workout_pdf, name='export_workout_pdf'),
    path('export-weight-pdf/', views.export_weight_pdf, name='export_weight_pdf'),
    
    # AI Coach feature
    path('ai-coach/', views.ai_coach_view, name='ai_coach'),
    path('ai-coach-api/', views.ai_coach_api, name='ai_coach_api'),
    
    # Chart Data APIs
    path('personal-best-progress-api/', views.personal_best_progress_api, name='personal_best_progress_api'),
    path('weight-progress-api/', views.weight_progress_api, name='weight_progress_api'),
    path('performance-metrics-api/', views.performance_metrics_api, name='performance_metrics_api'),
    path('ai-coach-api/<int:question_id>/', views.ai_coach_question_api, name='ai_coach_question_api'),
]

# Add this to serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
