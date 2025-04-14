from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.password_validation import validate_password
from .models import Event, Solution, User, File
from django.core.exceptions import ValidationError
from django.conf import settings
import os
import requests
import time

def validate_file_viruses(value):
    """
    Проверка файла на вирусы с использованием VirusTotal API
    Оптимизированная версия без бесконечного опроса
    """
    # Отключаем проверку для локальной разработки
    if settings.DEBUG:
        return
        
    try:
        url = "https://www.virustotal.com/api/v3/files"
        headers = {
            "accept": "application/json",
            "x-apikey": "822d4b03712a0eb941610876810053e4d516fd251d9f8a014628a220899f7ba4"
        }
        
        # Подготовка файла для загрузки
        files = {
            "file": (value.name, value.file, value.content_type)
        }
        
        # Отправляем файл в VirusTotal с таймаутом
        response = requests.post(url, files=files, headers=headers, timeout=10)
        if response.status_code != 200:
            # Не блокируем загрузку при ошибке API, просто логируем
            print(f"Ошибка при проверке файла на вирусы: {response.status_code}")
            return
        
        # Получаем ID анализа
        result = response.json()
        analysis_id = result.get("data", {}).get("id")
        if not analysis_id:
            print("Не удалось получить ID анализа файла")
            return
        
        # Запрашиваем результаты анализа один раз с таймаутом
        analysis_url = f"https://www.virustotal.com/api/v3/analyses/{analysis_id}"
        analysis_response = requests.get(analysis_url, headers=headers, timeout=10)
        
        if analysis_response.status_code != 200:
            print(f"Ошибка при получении результатов анализа: {analysis_response.status_code}")
            return
        
        # Проверяем результаты
        analysis_result = analysis_response.json()
        stats = analysis_result.get("data", {}).get("attributes", {}).get("stats", {})
        
        # Выводим статистику сканирования
        print("Статистика сканирования:")
        print(f"Malicious: {stats.get('malicious', 0)}")
        print(f"Suspicious: {stats.get('suspicious', 0)}")
        print(f"Undetected: {stats.get('undetected', 0)}")
        print(f"Harmless: {stats.get('harmless', 0)}")
        print("____________________________")
        
        # Проверяем только если анализ полностью завершен
        status = analysis_result.get("data", {}).get("attributes", {}).get("status")
        if status == "completed" and stats.get("malicious", 0) > 0:
            raise ValidationError("Файл содержит вирусы и не может быть загружен.")
            
    except requests.RequestException as e:
        # При сетевых проблемах не блокируем загрузку
        print(f"Сетевая ошибка при проверке на вирусы: {str(e)}")
    except Exception as e:
        print(f"Непредвиденная ошибка при проверке на вирусы: {str(e)}")

def validate_file_extension(value):
    """Проверка расширения файла"""
    ext = os.path.splitext(value.name.lower())[1]
    if ext not in settings.ALLOWED_UPLOAD_EXTENSIONS:
        raise ValidationError(
            f'Недопустимый тип файла. Разрешены: {", ".join(settings.ALLOWED_UPLOAD_EXTENSIONS)}'
        )

def validate_file_size(value):
    """Проверка размера файла"""
    if value.size > settings.MAX_UPLOAD_SIZE:
        max_size_mb = settings.MAX_UPLOAD_SIZE / (1024 * 1024)
        raise ValidationError(f'Размер файла превышает {max_size_mb} MB.')

def validate_max_length(value):
    """Проверка максимальной длины пароля"""
    max_length = 20  # Установите максимальную длину пароля
    if len(value) > max_length:
        raise ValidationError(f'Пароль не должен превышать {max_length} символов.')

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    password1 = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput,
        validators=[validate_max_length]
    )
    password2 = forms.CharField(
        label="Подтверждение пароля",
        widget=forms.PasswordInput,
        validators=[validate_max_length]
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('Пароли не совпадают!')
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user

class EventForm(forms.ModelForm):
    uploaded_file = forms.FileField(
        required=True,
        label="Файл",
        validators=[validate_file_extension, validate_file_size, validate_file_viruses],
        help_text="Загрузите файл. Это обязательное поле."
    )
    
    class Meta:
        model = Event
        fields = ['title', 'description', 'limit_date']
        widgets = {
            'limit_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }
        labels = {
            'title': 'Заголовок',
            'description': 'Описание',
            'limit_date': 'Срок сдачи',
        }
        help_texts = {
            'title': 'Введите название события',
            'description': 'Подробное описание события',
            'limit_date': 'Укажите дату и время окончания приема решений',
        }
    
    def clean_limit_date(self):
        """
        Проверяет, что срок сдачи не находится в прошлом
        """
        limit_date = self.cleaned_data.get('limit_date')
        
        if limit_date:
            from django.utils import timezone
            now = timezone.now()
            
            if limit_date < now:
                raise forms.ValidationError('Срок сдачи не может быть в прошлом. Укажите актуальную дату.')
        
        return limit_date

class SolutionForm(forms.ModelForm):
    file = forms.FileField(
        required=False, 
        label="Файл",
        validators=[validate_file_extension, validate_file_size, validate_file_viruses]
    )
    
    class Meta:
        model = Solution
        fields = ['description']
        labels = {
            'description': 'Описание',
        }
        help_texts = {
            'description': 'Опишите ваше решение',
        }