from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django.utils import timezone
from datetime import timedelta
from .forms import UserRegistrationForm, EventForm, SolutionForm
from .models import Event, Solution, File, User, LoginAttempt
import os
from django.conf import settings
from django.http import FileResponse, HttpResponseNotFound
from django.utils.text import slugify
from .utils import secure_file_upload
from django.db.models import Prefetch
from django.db import models
from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_encode
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
from django.contrib.auth.tokens import default_token_generator
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from django.views.decorators.cache import cache_page
from django.views.decorators.cache import cache_control
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache


def custom_login(request):
    """
    Пользовательское представление для входа с защитой от брутфорса.
    Блокирует доступ после 5 неудачных попыток в течение часа.
    """
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # Получаем IP адрес
        ip_address = request.META.get('REMOTE_ADDR', '0.0.0.0')
        
        # Проверяем количество попыток за последний час
        one_hour_ago = timezone.now() - timedelta(hours=1)
        attempts = LoginAttempt.objects.filter(
            username=username, 
            ip_address=ip_address,
            attempt_time__gte=one_hour_ago
        ).count()
        
        # Если попыток больше 5, блокируем доступ
        if attempts >= 5:
            messages.error(request, 'Слишком много неудачных попыток входа. Ваш аккаунт временно заблокирован.')
            return render(request, 'albedo/lockout.html')
        
        # Пытаемся аутентифицировать пользователя
        user = authenticate(request, username=username, password=password)
        
        if user is not None and user.active:
            login(request, user)
            # Успешный вход - удаляем записи о попытках
            LoginAttempt.objects.filter(username=username, ip_address=ip_address).delete()
            return redirect('event_list')
        else:
            # Неудачная попытка - записываем
            LoginAttempt.objects.create(username=username, ip_address=ip_address)
            if user and not user.active:
                messages.error(request, 'Ваш аккаунт заблокирован администратором.')
            else:
                messages.error(request, 'Неверное имя пользователя или пароль')
    else:
        form = AuthenticationForm()
    
    return render(request, 'albedo/login.html', {'form': form})

def home(request):
    # Получаем все события, сначала "в процессе", затем "закрытые", и сортируем по дате создания (новые сначала)
    events = Event.objects.filter(user__active=True).order_by('-status', '-created_at')
    return render(request, 'albedo/home.html', {'events': events})

EMAIL_HOST = "smtp.mail.ru"
EMAIL_PORT = 465
EMAIL_HOST_USER = settings.EMAIL_HOST_USER
EMAIL_HOST_PASSWORD = settings.EMAIL_HOST_PASSWORD  # пароль приложения из настроек Mail.ru


def send_verification_email(request, username, email, uid, token):
    subject = 'Подтверждение вашей почты'
    current_site = request.get_host()
    verification_link = f"http://{current_site}/verify-email/{uid}/{token}/"
    message = f"Здравствуйте, {username}!\n\nДля подтверждения вашего email перейдите по ссылке:\n{verification_link}\n\nЕсли вы не регистрировались, проигнорируйте это сообщение."
    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_HOST_USER
        msg["To"] = email
        msg["Subject"] = subject
        msg.attach(MIMEText(message, "plain"))

        server = smtplib.SMTP_SSL(EMAIL_HOST, EMAIL_PORT)
        server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
        server.sendmail(EMAIL_HOST_USER, email, msg.as_string())
        server.quit()
    except Exception as e:
        print("Ошибка при отправке письма:", e)

def verify_email(request, uidb64, token):
    try:
        username = urlsafe_base64_decode(uidb64).decode()
        user_data = request.session.get('user_data')
        password = request.session.get('user_password')

        if not user_data or user_data['username'] != username:
            raise ValueError('Неверные данные сессии.')

        user = User(**user_data)
        if not default_token_generator.check_token(user, token):
            raise ValueError('Неверный токен.')


        user.set_password(password)
        user.save()
        del request.session['user_data']
        del request.session['user_password']
        messages.success(request, 'Ваш email успешно подтвержден! Теперь вы можете войти в свой аккаунт.')
        return redirect('login')
    except (TypeError, ValueError, OverflowError, User.DoesNotExist) as e:
        messages.error(request, 'Неверная или устаревшая ссылка для подтверждения почты.')
        return render(request, 'albedo/verify_email.html', {'status': 'error','error': e})
    
def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            # Извлекаем данные формы
            user_data = form.cleaned_data.copy()
            password = user_data.pop('password1')  # Пароль храним отдельно
            user_data.pop('password2')  # Удаляем второй пароль, он не нужен

            # Генерация UID и токена
            uid = urlsafe_base64_encode(force_bytes(form.cleaned_data['username']))
            token = default_token_generator.make_token(User(username=form.cleaned_data['username'], email=form.cleaned_data['email']))

            # Сохраняем данные формы в сессии (без сохранения в БД)
            request.session['user_data'] = user_data
            request.session['user_password'] = password

            send_verification_email(request, user_data['username'], user_data['email'], uid, token)

            messages.success(request, 'Регистрация почти завершена! Проверьте свою почту для подтверждения.')
            #user = form.save(commit=False)
            #user.is_active = False
            #user.save()
            #send_verification_email()
            #login(request, user)
            #messages.success(request, 'Регистрация успешно завершена!')
            return redirect('event_list')
        else:
            # Print form errors to console for debugging
            print(form.errors)
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
    else:
        form = UserRegistrationForm()
    return render(request, 'albedo/register.html', {'form': form})

@login_required
def event_list(request):
    # Фильтруем события, созданные только активными пользователями, и сортируем: сначала "в процессе", затем по дате создания
    events = Event.objects.filter(user__active=True).order_by('-status', '-created_at')
    return render(request, 'albedo/event_list.html', {'events': events})

@login_required
def event_detail(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    
    # Проверяем, не истек ли срок сдачи и обновляем статус при необходимости
    event.update_status_if_expired()
    
    # Изменяем запрос, чтобы не пытаться получить cloudinary_url
    # Используем select_related для оптимизации запросов
    event = Event.objects.select_related('user').select_related('file').get(id=event_id)
    
    # Получаем связанные решения
    solutions = Solution.objects.filter(event=event).select_related('user')
    
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
        
        # Проверяем наличие файла как на уровне формы, так и на уровне представления
        if 'uploaded_file' not in request.FILES:
            messages.error(request, 'Необходимо прикрепить файл к событию.')
            return render(request, 'albedo/event_form.html', {'form': form})
            
        if form.is_valid():
            event = form.save(commit=False)
            event.user = request.user
            
            # Обработка загрузки файла с проверками безопасности
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
            
            # Сохраняем объект файла
            try:
                file_obj.save()
            except Exception as e:
                print(f"Ошибка при сохранении файла: {str(e)}")
                messages.error(request, f"Ошибка при загрузке файла: {str(e)}")
                return render(request, 'albedo/event_form.html', {'form': form})
            
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
    """Загрузка файла по его ID"""
    file_obj = get_object_or_404(File, id=file_id)
    
    # Путь к файлу в локальной файловой системе
    file_path = os.path.join(settings.MEDIA_ROOT, file_obj.file_path)
    
    if os.path.exists(file_path):
        # Открываем файл и возвращаем для скачивания
        response = FileResponse(open(file_path, 'rb'))
        response['Content-Disposition'] = f'attachment; filename="{file_obj.file_name}"'
        return response
    else:
        messages.error(request, 'Запрашиваемый файл не найден')
        return HttpResponseNotFound('Запрашиваемый файл не найден')

@login_required
def preview_file(request, file_id):
    """Просмотр файла без скачивания (если возможно)"""
    file_obj = get_object_or_404(File, id=file_id)
    
    # Для локальной файловой системы отдаем файл напрямую
    file_path = os.path.join(settings.MEDIA_ROOT, file_obj.file_path)
    
    if os.path.exists(file_path):
        # Для изображений и PDF отображаем в браузере, для остальных предлагаем скачать
        content_type = file_obj.mime_type
        inline_types = ['image/', 'application/pdf', 'video/', 'text/']
        
        response = FileResponse(open(file_path, 'rb'), content_type=content_type)
        
        # Проверяем, можно ли отобразить файл в браузере
        is_inline = any(content_type.startswith(t) for t in inline_types)
        
        if is_inline:
            response['Content-Disposition'] = f'inline; filename="{file_obj.file_name}"'
        else:
            # Если тип файла не поддерживает предпросмотр, предлагаем скачать
            response['Content-Disposition'] = f'attachment; filename="{file_obj.file_name}"'
            
        return response
    else:
        messages.error(request, 'Запрашиваемый файл не найден')
        return HttpResponseNotFound('Запрашиваемый файл не найден')

@login_required
def add_solution(request, event_id):
    # Проверка на блокировку пользователя
    if not is_active_user(request.user):
        messages.error(request, 'Вы заблокированы. Добавление решений недоступно.')
        return redirect('event_detail', event_id=event_id)
        
    event = get_object_or_404(Event, id=event_id)
    
    # Проверяем, не истек ли срок сдачи и обновляем статус при необходимости
    event.update_status_if_expired()
    
    # Проверяем статус события после возможного обновления
    if event.status == 'closed':
        messages.error(request, 'Событие закрыто. Добавление решений невозможно.')
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
                
                # Сохраняем объект файла с обработкой ошибок
                try:
                    file_obj.save()
                except Exception as e:
                    print(f"Ошибка при сохранении файла: {str(e)}")
                    messages.error(request, f"Ошибка при загрузке файла: {str(e)}")
                    return render(request, 'albedo/solution_form.html', {'form': form, 'event': event})
                
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
@cache_control(private=True, max_age=3600)
def profile(request):
    """Отображение профиля текущего пользователя"""
    # Получаем решения текущего пользователя
    user_solutions = Solution.objects.filter(user=request.user).order_by('-created_at')
    
    # Получаем события, созданные пользователем: сначала "в процессе", затем "закрытые"
    user_events = Event.objects.filter(user=request.user).order_by('-status', '-created_at')
    
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

def custom_404_view(request, exception=None):
    """Кастомная страница 404"""
    response = render(request, 'albedo/404.html', status=404)
@csrf_exempt
@cache_page(60 * 15)
def about(request):
    # Отключаем сессию
    if hasattr(request, 'session'):
        del request.session

    response = render(request, 'albedo/about.html')
    response['Vary'] = 'Accept-Encoding'  # Укажите только нужные заголовки
    return response