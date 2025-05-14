from django.shortcuts import redirect
from django.contrib import messages
from django.urls import resolve
import re

class UserBlockStatusMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Проверяем статус пользователя только если он аутентифицирован
        if request.user.is_authenticated and not request.user.active:
            # Получаем имя текущего URL
            current_url_name = resolve(request.path_info).url_name
            
            # Список URL, которые доступны даже заблокированным пользователям
            allowed_urls = ['logout', 'profile', 'home', 'event_list', 'event_detail']
            
            # Если пользователь пытается получить доступ к запрещенной функции
            if current_url_name not in allowed_urls:
                messages.warning(request, 'Вы заблокированы. Некоторые функции сайта недоступны.')
                # Перенаправление на домашнюю страницу
                return redirect('home')
        
        response = self.get_response(request)
        return response

class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Добавляем заголовки безопасности
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Content-Security-Policy'] = "default-src 'self'; " \
                                            "script-src 'self' https://code.jquery.com https://cdn.jsdelivr.net https://stackpath.bootstrapcdn.com 'unsafe-inline'; " \
                                            "style-src 'self' https://stackpath.bootstrapcdn.com https://cdnjs.cloudflare.com 'unsafe-inline'; " \
                                            "img-src 'self' data:; " \
                                            "font-src 'self' https://cdnjs.cloudflare.com;"
        
        return response

# Middleware для проверки путей загрузки файлов на инъекции
class PathTraversalProtectionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.path_traversal_pattern = re.compile(r'\.\./')

    def __call__(self, request):
        # Проверяем параметры пути на наличие path traversal
        if 'file_id' in request.path:
            path = request.path
            if self.path_traversal_pattern.search(path):
                messages.error(request, 'Недопустимый путь к файлу.')
                return redirect('home')
                
        response = self.get_response(request)
        return response