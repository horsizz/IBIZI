from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import UserRegistrationForm, EventForm, SolutionForm
from .models import Event, Solution, File, User
import os
from django.conf import settings
from django.http import FileResponse, HttpResponseNotFound
from django.utils.text import slugify
from .utils import secure_file_upload  # Импортируем новую функцию

def home(request):
    # Получаем все события, отсортированные по дате создания (новые сначала)
    events = Event.objects.all().order_by('-created_at')
    return render(request, 'albedo/home.html', {'events': events})

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Регистрация успешно завершена!')
            return redirect('event_list')
        else:
            # Print form errors to console for debugging
            print(form.errors)
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
    else:
        form = UserRegistrationForm()
    return render(request, 'albedo/register.html', {'form': form})

# @login_required
def event_list(request):
    events = Event.objects.all().order_by('-created_at')
    return render(request, 'albedo/event_list.html', {'events': events})

@login_required
def event_detail(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    solutions = event.solutions.all()
    return render(request, 'albedo/event_detail.html', {
        'event': event,
        'solutions': solutions
    })

def is_active_user(user):
    """Проверяет, активен ли пользователь"""
    return user.is_authenticated and user.active

@login_required
def create_event(request):
    # Проверка на блокировку пользователя
    if not is_active_user(request.user):
        messages.error(request, 'Вы заблокированы. Создание событий недоступно.')
        return redirect('event_list')
        
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)
            event.user = request.user
            
            # Обработка загрузки файла с проверками безопасности
            if 'uploaded_file' in request.FILES:
                uploaded_file = request.FILES['uploaded_file']
                
                # Создаем директорию для загрузки, если она не существует
                upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
                
                # Используем нашу функцию безопасной загрузки
                file_info, errors = secure_file_upload(uploaded_file, upload_dir)
                
                if errors:
                    for error in errors:
                        messages.error(request, error)
                    return render(request, 'albedo/event_form.html', {'form': form})
                
                # Создаем новый объект File
                file_obj = File(
                    file_name=file_info['file_name'],
                    size=file_info['size'],
                    file_path=file_info['file_path'],
                    mime_type=file_info['mime_type']
                )
                file_obj.save()
                
                # Связываем файл с событием
                event.file = file_obj
            
            event.save()
            messages.success(request, 'Событие успешно создано!')
            return redirect('event_detail', event_id=event.id)
    else:
        form = EventForm()
    return render(request, 'albedo/event_form.html', {'form': form})

@login_required
def download_file(request, file_id):
    """View to download a file by its ID"""
    file_obj = get_object_or_404(File, id=file_id)
    
    # Construct full path to file
    file_path = os.path.join(settings.MEDIA_ROOT, file_obj.file_path)
    
    # Check if file exists
    if os.path.exists(file_path):
        # Return file as response with proper filename
        response = FileResponse(open(file_path, 'rb'))
        response['Content-Disposition'] = f'attachment; filename="{file_obj.file_name}"'
        return response
    else:
        return HttpResponseNotFound('Requested file not found')

@login_required
def add_solution(request, event_id):
    # Проверка на блокировку пользователя
    if not is_active_user(request.user):
        messages.error(request, 'Вы заблокированы. Добавление решений недоступно.')
        return redirect('event_detail', event_id=event_id)
        
    event = get_object_or_404(Event, id=event_id)
    if event.status == 'closed':
        messages.error(request, 'This event is closed.')
        return redirect('event_detail', event_id=event.id)
    
    if request.method == 'POST':
        form = SolutionForm(request.POST, request.FILES)
        if form.is_valid():
            solution = form.save(commit=False)
            solution.event = event
            solution.user = request.user
            
            # Обработка загрузки файла с проверками безопасности
            if 'file' in request.FILES:
                uploaded_file = request.FILES['file']
                
                # Создаем директорию для загрузки
                upload_dir = os.path.join(settings.MEDIA_ROOT, 'solutions')
                
                # Используем нашу функцию безопасной загрузки
                file_info, errors = secure_file_upload(uploaded_file, upload_dir)
                
                if errors:
                    for error in errors:
                        messages.error(request, error)
                    return render(request, 'albedo/solution_form.html', {'form': form, 'event': event})
                
                # Создаем новый объект File
                file_obj = File(
                    file_name=file_info['file_name'],
                    size=file_info['size'],
                    file_path=file_info['file_path'],
                    mime_type=file_info['mime_type']
                )
                file_obj.save()
                
                # Связываем файл с решением
                solution.file = file_obj
                
            solution.save()
            return redirect('event_detail', event_id=event.id)
    else:
        form = SolutionForm()
    return render(request, 'albedo/solution_form.html', {'form': form, 'event': event})

def logout_view(request):
    """Простая функция для корректного завершения сессии пользователя"""
    logout(request)  # Явно завершаем сессию
    messages.success(request, 'Вы успешно вышли из системы')
    return redirect('home')

@login_required
def profile(request):
    """Отображение профиля текущего пользователя"""
    # Получаем решения текущего пользователя
    user_solutions = Solution.objects.filter(user=request.user).order_by('-created_at')
    
    # Получаем события, созданные пользователем
    user_events = Event.objects.filter(user=request.user).order_by('-created_at')
    
    context = {
        'user': request.user,
        'solutions': user_solutions,
        'events': user_events
    }
    
    return render(request, 'albedo/profile.html', context)

def is_admin(user):
    """Проверка, является ли пользователь администратором"""
    return user.is_authenticated and user.role == 'admin'

@login_required
def user_list(request):
    """Страница со списком пользователей (только для администраторов)"""
    if not is_admin(request.user):
        messages.error(request, 'У вас нет доступа к этой странице.')
        return redirect('home')
        
    users = User.objects.all().order_by('-date_joined')
    return render(request, 'albedo/user_list.html', {'users': users})

@login_required
def toggle_user_status(request, user_id):
    """Блокировка/разблокировка пользователя"""
    if not is_admin(request.user):
        messages.error(request, 'У вас нет прав для выполнения этого действия.')
        return redirect('home')
    
    target_user = get_object_or_404(User, id=user_id)
    
    # Нельзя блокировать администраторов
    if target_user.role == 'admin':
        messages.error(request, 'Невозможно заблокировать администратора.')
        return redirect('user_list')
    
    # Инвертируем статус активности
    target_user.active = not target_user.active
    target_user.save()
    
    status = 'разблокирован' if target_user.active else 'заблокирован'
    messages.success(request, f'Пользователь {target_user.username} {status}.')
    
    return redirect('user_list')

@login_required
def delete_event(request, event_id):
    """Удаление события"""
    if not is_admin(request.user):
        messages.error(request, 'У вас нет прав для выполнения этого действия.')
        return redirect('home')
    
    event = get_object_or_404(Event, id=event_id)
    event.delete()
    
    messages.success(request, 'Событие успешно удалено.')
    return redirect('event_list')

@login_required
def delete_solution(request, solution_id):
    """Удаление решения"""
    if not is_admin(request.user):
        messages.error(request, 'У вас нет прав для выполнения этого действия.')
        return redirect('home')
    
    solution = get_object_or_404(Solution, id=solution_id)
    event_id = solution.event.id
    solution.delete()
    
    messages.success(request, 'Решение успешно удалено.')
    return redirect('event_detail', event_id=event_id)