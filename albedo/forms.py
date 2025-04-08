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
    """Проверка файла на вирусы"""
    url = "https://www.virustotal.com/api/v3/files"
    headers = {
        "accept": "application/json",
        "x-apikey": "822d4b03712a0eb941610876810053e4d516fd251d9f8a014628a220899f7ba4"  # Replace with your actual VirusTotal API key
    }
    
    # Prepare the file for upload
    files = {
        "file": (value.name, value.file, value.content_type)
    }
    
    # Send the file to VirusTotal
    response = requests.post(url, files=files, headers=headers)
    if response.status_code != 200:
        raise ValidationError("Ошибка при проверке файла на вирусы.")
    
    # Parse the response to get the analysis ID
    result = response.json()
    analysis_id = result.get("data", {}).get("id")
    if not analysis_id:
        raise ValidationError("Не удалось получить ID анализа файла.")
    
    # Poll the analysis results
    analysis_url = f"https://www.virustotal.com/api/v3/analyses/{analysis_id}"
    while True:
        analysis_response = requests.get(analysis_url, headers=headers)
        if analysis_response.status_code != 200:
            raise ValidationError("Ошибка при получении результатов анализа файла.")
        
        analysis_result = analysis_response.json()
        status = analysis_result.get("data", {}).get("attributes", {}).get("status")
        
        # Print scan statistics
        stats = analysis_result.get("data", {}).get("attributes", {}).get("stats", {})
        print("Статистика сканирования:")
        print(f"Malicious: {stats.get('malicious', 0)}")
        print(f"Suspicious: {stats.get('suspicious', 0)}")
        print(f"Undetected: {stats.get('undetected', 0)}")
        print(f"Harmless: {stats.get('harmless', 0)}")
        print(f"Timeout: {stats.get('timeout', 0)}")
        print(f"Failures: {stats.get('failure', 0)}")
        print(f"Type Unsupported: {stats.get('type-unsupported', 0)}")
        print("____________________________")
        
        if status == "completed":
            # Analysis is complete, check the results
            malicious = stats.get("malicious", 0)
            if malicious > 0:
                raise ValidationError("Файл содержит вирусы и не может быть загружен.")
            break
        else:
            # Wait and retry
            time.sleep(5)

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
        required=False, 
        label="Файл",
        validators=[validate_file_extension, validate_file_size, validate_file_viruses]
    )
    
    class Meta:
        model = Event
        fields = ['title', 'description', 'limit_date']
        widgets = {
            'limit_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

class SolutionForm(forms.ModelForm):
    file = forms.FileField(
        required=False, 
        label="Файл",
        validators=[validate_file_extension, validate_file_size, validate_file_viruses]
    )
    
    class Meta:
        model = Solution
        fields = ['description']