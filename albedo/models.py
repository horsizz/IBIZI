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
    file_name = models.CharField(max_length=255, verbose_name="Имя файла")
    size = models.PositiveIntegerField(verbose_name="Размер")
    file_path = models.CharField(max_length=255, verbose_name="Путь к файлу")
    mime_type = models.CharField(max_length=255, verbose_name="MIME тип")
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата загрузки")
    cloudinary_url = models.URLField(max_length=1000, blank=True, null=True, verbose_name="Cloudinary URL")
    preview_url = models.URLField(max_length=1000, blank=True, null=True, verbose_name="URL предпросмотра")

    class Meta:
        verbose_name = "Файл"
        verbose_name_plural = "Файлы"

    def __str__(self):
        return self.file_name


class Event(models.Model):
    STATUS_CHOICES = (
        ('in_progress', 'В процессе'),
        ('closed', 'Закрыто'),
    )

    title = models.CharField(max_length=28, verbose_name="Заголовок")
    description = models.TextField(blank=True, max_length=300, verbose_name="Описание")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    status = models.CharField(
        max_length=11,
        choices=STATUS_CHOICES,
        default='in_progress',
        verbose_name="Статус"
    )
    limit_date = models.DateTimeField(null=True, blank=True, verbose_name="Срок сдачи")
    # Связь с пользователем (кто создал или владеет ивентом)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='events',
        verbose_name="Пользователь"
    )
    # Связь с файлом (например, общий файл или описание)
    file = models.ForeignKey(
        File,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='events',
        verbose_name="Файл"
    )

    class Meta:
        verbose_name = "Событие"
        verbose_name_plural = "События"

    def __str__(self):
        return self.title
        
    def is_expired(self):
        """Проверяет, истек ли срок сдачи события"""
        if self.limit_date and self.status == 'in_progress':
            from django.utils import timezone
            return self.limit_date < timezone.now()
        return False

    def update_status_if_expired(self):
        """Обновляет статус события, если срок сдачи истек"""
        if self.is_expired():
            self.status = 'closed'
            self.save(update_fields=['status'])
            return True
        return False


class Solution(models.Model):
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name='solutions',
        verbose_name="Событие"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='solutions',
        verbose_name="Пользователь"
    )
    file = models.ForeignKey(
        File,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='solutions',
        verbose_name="Файл"
    )
    description = models.TextField(blank=True, verbose_name="Описание")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Решение"
        verbose_name_plural = "Решения"

    def __str__(self):
        return f"Решение от {self.user.username} для {self.event.title}"
