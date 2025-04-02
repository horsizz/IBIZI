import os
import re
import mimetypes
import hashlib
import uuid

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
    Создает безопасное имя файла, сохраняя расширение
    """
    base, ext = os.path.splitext(filename)
    # Генерируем уникальное имя файла на основе UUID и хэша оригинального имени
    name_hash = hashlib.md5(base.encode()).hexdigest()[:8]
    safe_name = f"{uuid.uuid4().hex}_{name_hash}{ext}"
    return safe_name

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

def get_simple_mime_type(filename):
    """
    Получает MIME тип на основе расширения файла
    """
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type or 'application/octet-stream'  # Возвращаем generic type если не определен

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
    
    # Если все проверки пройдены, создаем безопасное имя файла
    safe_filename = sanitize_filename(file.name)
    
    # Создаем директорию, если она не существует
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, safe_filename)
    
    # Создаем относительный путь для хранения в базе
    relative_path = os.path.join(os.path.basename(upload_dir), safe_filename)
    
    # Определяем MIME тип на основе расширения
    mime_type = get_simple_mime_type(file.name)
    
    # Сохраняем файл
    with open(file_path, 'wb+') as destination:
        for chunk in file.chunks():
            destination.write(chunk)
    
    # Возвращаем информацию о файле
    file_info = {
        'file_name': file.name,  # Оригинальное имя для отображения
        'safe_name': safe_filename,  # Безопасное имя в файловой системе
        'file_path': relative_path,  # Путь для хранения в базе
        'size': file.size,
        'mime_type': mime_type
    }
    
    return file_info, None
