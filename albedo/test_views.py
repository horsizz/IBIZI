# Обычная функция для проверки кастомной 404 страницы

def test_404(request):
    """
    Это функция-дополнение, которая предоставляет URL для тестирования 
    кастомной 404 страницы без изменения DEBUG.
    """
    from django.template.response import TemplateResponse
    
    # Просто рендерим 404 страницу с нужным статусом
    context = {'request_path': request.path}
    response = TemplateResponse(request, 'albedo/404.html', context)
    response.status_code = 404
    return response
