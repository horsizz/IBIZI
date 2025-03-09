from django import forms
from django.contrib.auth.forms import UserCreationForm
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

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

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
