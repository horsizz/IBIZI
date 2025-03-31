from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.password_validation import validate_password
from .models import Event, Solution, User, File
from django.core.exceptions import ValidationError
from django.conf import settings
import os

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
        validators=[validate_file_extension, validate_file_size]
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
        validators=[validate_file_extension, validate_file_size]
    )
    
    class Meta:
        model = Solution
        fields = ['description']