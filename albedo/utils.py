import os
import re
import mimetypes
import hashlib
import uuid
import boto3
from django.conf import settings
import inspect
from django.db import connection

# Определяем безопасные расширения
ALLOWED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.pdf', '.xls', '.xlsx', '.doc', '.docx', '.txt', '.zip']

# Максимальный размер файла (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024

def check_file_extension(filename):
    """
    Проверяет, имеет ли файл разрешенное расширение
    """
    ext = os.path.splitext(filename.lower())[1]
    return ext in ALLOWED_EXTENSIONS

def check_file_size(file):
    """
    Проверяет, не превышает ли размер файла максимально допустимый
    """
    return file.size <= MAX_FILE_SIZE

def check_double_extensions(filename):
    """
    Проверяет наличие двойных расширений, что может быть попыткой обхода проверок
    """
    # Ищем паттерны типа file.jpg.php
    pattern = r'\.[a-z0-9]+\.[a-z0-9]+$'
    return not bool(re.search(pattern, filename.lower()))

def sanitize_filename(filename):
    """
    Создает безопасное имя файла с уникальным идентификатором
    """
    # Получаем базовое имя без пути
    base = os.path.basename(filename)
    
    # Получаем расширение
    name, ext = os.path.splitext(base)
    
    # Создаем хеш для уникальности
    unique_id = hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()[:8]
    
    # Создаем безопасное имя
    safe_name = f"{name}_{unique_id}{ext}"
    
    # Заменяем небезопасные символы
    safe_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', safe_name)
    
    return safe_name

def get_simple_mime_type(filename):
    """
    Получает MIME-тип файла на основе его расширения
    """
    mime, _ = mimetypes.guess_type(filename)
    return mime or 'application/octet-stream'

def scan_file_content(file):
    """
    Сканирует начало файла на наличие вредоносных паттернов
    """
    # Читаем первые 8 КБ файла для проверки заголовка
    content_start = file.read(8192)
    file.seek(0)  # Возвращаем указатель в начало файла
    
    # Паттерны для обнаружения потенциально вредоносного кода
    dangerous_patterns = [
        b'<?php', b'<%', b'<script', b'eval(', 
        b'document.write', b'exec(', b'system(', 
        b'import os', b'subprocess', b'fromCharCode'
    ]
    
    # Проверка на наличие опасных шаблонов
    for pattern in dangerous_patterns:
        if pattern in content_start:
            return False
    
    return True

def secure_file_upload(file, upload_dir):
    """
    Комплексная проверка и безопасная загрузка файла
    """
    errors = []
    
    # 1. Проверка размера
    if not check_file_size(file):
        errors.append(f"Файл слишком большой. Максимальный размер: {MAX_FILE_SIZE/1024/1024}MB.")
        return None, errors
    
    # 2. Проверка расширения
    if not check_file_extension(file.name):
        errors.append(f"Недопустимое расширение файла. Разрешены: {', '.join(ALLOWED_EXTENSIONS)}.")
        return None, errors
    
    # 3. Проверка на двойные расширения
    if not check_double_extensions(file.name):
        errors.append("Обнаружено двойное расширение файла.")
        return None, errors
    
    # 4. Проверка содержимого на вредоносный код
    if not scan_file_content(file):
        errors.append("В файле обнаружен потенциально опасный код.")
        return None, errors
    
    # Получаем оригинальное имя файла
    original_filename = file.name
    
    # Обеспечиваем уникальность имени файла, добавляя метку времени только если нужно
    import time
    base_name, ext = os.path.splitext(original_filename)
    filename = original_filename
    
    # Проверяем существование файла и при необходимости добавляем счетчик
    counter = 1
    file_path = os.path.join(upload_dir, filename)
    while os.path.exists(file_path):
        filename = f"{base_name}_{counter}{ext}"
        file_path = os.path.join(upload_dir, filename)
        counter += 1
    
    # Определяем MIME тип на основе расширения
    mime_type = get_simple_mime_type(file.name)
    
    # Загружаем файл локально
    try:
        # Создаем директорию, если она не существует
        os.makedirs(upload_dir, exist_ok=True)
        
        # Получаем относительный путь для хранения в БД
        relative_path = os.path.join(os.path.basename(upload_dir), filename)
        
        # Сохраняем файл
        with open(file_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
        
        # Возвращаем информацию о файле
        file_info = {
            'file_name': original_filename,
            'safe_name': filename,
            'file_path': relative_path,
            'size': file.size,
            'mime_type': mime_type
        }
        
        return file_info, None
        
    except Exception as e:
        errors.append(f"Ошибка при сохранении файла: {str(e)}")
        return None, errors
