from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('events/', views.event_list, name='event_list'),
    path('verify-email/<uidb64>/<token>/', views.verify_email, name='verify_email'),
    path('login/', auth_views.LoginView.as_view(template_name='albedo/login.html'), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),  # Новый URL для профиля
    path('event/new/', views.create_event, name='create_event'),
    path('event/<int:event_id>/', views.event_detail, name='event_detail'),
    path('event/<int:event_id>/solution/', views.add_solution, name='add_solution'),
    path('file/<int:file_id>/download/', views.download_file, name='download_file'),
    
    # Админ функции
    path('users/', views.user_list, name='user_list'),
    path('users/<int:user_id>/toggle/', views.toggle_user_status, name='toggle_user_status'),
    path('event/<int:event_id>/delete/', views.delete_event, name='delete_event'),
    path('solution/<int:solution_id>/delete/', views.delete_solution, name='delete_solution'),
]
