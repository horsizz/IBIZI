from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .test_views import test_404

urlpatterns = [
    path('', views.home, name='home'),
    path('test-404/', test_404, name='test_404'),  # Тестовый URL для 404
    path('register/', views.register, name='register'),
    path('events/', views.event_list, name='event_list'),
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='albedo/password_reset_form.html', email_template_name='albedo/password_reset_email.html', subject_template_name='albedo/password_reset_subject.txt'), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='albedo/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='albedo/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='albedo/password_reset_complete.html'), name='password_reset_complete'),    path('verify-email/<uidb64>/<token>/', views.verify_email, name='verify_email'),
    path('login/', views.custom_login, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),  # Новый URL для профиля
    path('event/new/', views.create_event, name='create_event'),
    path('event/<int:event_id>/', views.event_detail, name='event_detail'),
    path('event/<int:event_id>/solution/', views.add_solution, name='add_solution'),
    path('file/<int:file_id>/download/', views.download_file, name='download_file'),
    path('file/<int:file_id>/preview/', views.preview_file, name='preview_file'),  # Новый маршрут для предпросмотра
    
    # Админ функции
    path('users/', views.user_list, name='user_list'),
    path('users/<int:user_id>/toggle/', views.toggle_user_status, name='toggle_user_status'),
    path('event/<int:event_id>/delete/', views.delete_event, name='delete_event'),
    path('solution/<int:solution_id>/delete/', views.delete_solution, name='delete_solution'),
]
