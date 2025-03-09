from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = (
        ('user', 'Пользователь'),
        ('admin', 'Администратор'),
    )
    
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=5, choices=ROLE_CHOICES, default='user')
    active = models.BooleanField(default=True)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    def __str__(self):
        return self.username
    
    def get_role_display(self):
        """Возвращает отображаемое значение роли"""
        return dict(self.ROLE_CHOICES).get(self.role, 'Неизвестно')


class File(models.Model):
    file_name = models.CharField(max_length=255)
    size = models.PositiveIntegerField()
    file_path = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=50)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file_name


class Event(models.Model):
    STATUS_CHOICES = (
        ('in_progress', 'In Progress'),
        ('closed', 'Closed'),
    )

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=11,
        choices=STATUS_CHOICES,
        default='in_progress'
    )
    limit_date = models.DateTimeField(null=True, blank=True)
    # Связь с пользователем (кто создал или владеет ивентом)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='events'
    )
    # Связь с файлом (например, общий файл или описание)
    file = models.ForeignKey(
        File,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='events'
    )

    def __str__(self):
        return self.title


class Solution(models.Model):
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='solutions'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='solutions'
    )
    file = models.ForeignKey(
        File,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='solutions'
    )
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Solution by {self.user.username} for {self.event.title}"
