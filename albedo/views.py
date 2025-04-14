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


def home(request):
    # Получаем все события, отсортированные по дате создания (новые сначала)
    events = Event.objects.filter(user__active=True).order_by('-created_at')
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
    # Фильтруем события, созданные только активными пользователями
    events = Event.objects.filter(user__active=True).order_by('-created_at')
    return render(request, 'albedo/event_list.html', {'events': events})

@login_required
def event_detail(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    
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
            
            # Проверяем, есть ли cloudinary_url в file_info и можно ли добавить это поле в модель
            # Используем try-except для обработки возможных ошибок с отсутствующим полем
            try:
                if 'cloudinary_url' in file_info:
                    # Проверяем, существует ли поле cloudinary_url в модели
                    if hasattr(File, 'cloudinary_url'):
                        file_obj.cloudinary_url = file_info['cloudinary_url']
            except Exception as e:
                # Логируем ошибку, но позволяем процессу продолжиться
                print(f"Ошибка при установке cloudinary_url: {str(e)}")
                
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
    """View to download a file by its ID"""
    file_obj = get_object_or_404(File, id=file_id)
    
    if settings.USE_CLOUDINARY:
        import cloudinary
        import cloudinary.uploader
        import cloudinary.api
        
        try:
            # Определяем тип ресурса на основе расширения файла
            name, ext = os.path.splitext(file_obj.file_name.lower())
            resource_type = "raw"  # По умолчанию для документов
            if ext in ['.jpg', '.jpeg', '.png', '.gif']:
                resource_type = "image"
            elif ext in ['.mp4', '.mov', '.avi']:
                resource_type = "video"
            
            # Получаем имя облака из настроек
            cloud_name = settings.CLOUDINARY_STORAGE.get('CLOUD_NAME')
            if not cloud_name:
                # Если CLOUD_NAME не установлен в CLOUDINARY_STORAGE, получаем его из конфигурации cloudinary
                cloud_name = cloudinary.config().cloud_name
                
            if not cloud_name:
                raise ValueError("Cloudinary cloud_name не настроен")
                
            # Формируем правильный public_id для Cloudinary
            public_id = file_obj.file_path
            
            # Если public_id содержит префикс папки, обрабатываем его
            folder_prefix = ""
            if '/' in public_id:
                parts = public_id.split('/')
                if parts[0] in ['uploads', 'solutions']:
                    folder_prefix = parts[0] + "/"
                    public_id = '/'.join(parts[1:])
            
            # Используем функцию cloudinary.utils.cloudinary_url для создания корректного URL
            download_url = cloudinary.utils.cloudinary_url(
                folder_prefix + public_id,
                resource_type=resource_type,
                type="upload",
                secure=True,
                format=ext.lstrip('.') if ext else None,
                attachment=True
            )[0]
            
            print(f"DEBUG - Download URL: {download_url}")
            
            # Перенаправляем на URL для скачивания
            return redirect(download_url)
        except Exception as e:
            print(f"Ошибка при скачивании: {str(e)}")
            messages.error(request, f'Ошибка при получении файла: {str(e)}')
            return redirect('event_list')
    else:
        # Локальная файловая система
        file_path = os.path.join(settings.MEDIA_ROOT, file_obj.file_path)
        
        if os.path.exists(file_path):
            response = FileResponse(open(file_path, 'rb'))
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
                
                # Безопасно устанавливаем cloudinary_url, если он есть
                try:
                    if 'cloudinary_url' in file_info and hasattr(File, 'cloudinary_url'):
                        file_obj.cloudinary_url = file_info['cloudinary_url']
                except Exception as e:
                    print(f"Ошибка при установке cloudinary_url: {str(e)}")
                
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