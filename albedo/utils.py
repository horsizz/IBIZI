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
    
    # Если все проверки пройдены, создаем безопасное имя файла
    safe_filename = sanitize_filename(file.name)
    
    # Определяем MIME тип на основе расширения
    mime_type = get_simple_mime_type(file.name)
    
    # Создаем поддиректорию на основе хеша для лучшей организации
    subdir = hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()[:8]
    
    if settings.USE_CLOUDINARY:
        # Загружаем файл в Cloudinary
        import cloudinary
        import cloudinary.uploader
        
        try:
            # Создаем более безопасное имя для Cloudinary
            name, ext = os.path.splitext(safe_filename)
            safe_id = hashlib.md5(name.encode()).hexdigest()[:12]
            cloudinary_filename = f"{safe_id}{ext}"
            
            # Определяем путь хранения файла в Cloudinary (более короткий и без спецсимволов)
            cloudinary_folder = os.path.basename(upload_dir)
            public_id = f"{cloudinary_folder}/{subdir}/{cloudinary_filename}"
            
            # Определяем тип ресурса на основе расширения
            resource_type = "raw"  # По умолчанию для документов
            if ext.lower() in ['.jpg', '.jpeg', '.png', '.gif']:
                resource_type = "image"
            elif ext.lower() in ['.mp4', '.mov', '.avi']:
                resource_type = "video"
            
            # Загружаем файл в Cloudinary
            upload_result = cloudinary.uploader.upload(
                file,
                public_id=public_id,
                resource_type=resource_type,
                overwrite=True,
                use_filename=True
            )
            
            # Сохраняем URL из результата загрузки
            secure_url = upload_result.get('secure_url')
            
            # Создаем URL для скачивания с параметром fl_attachment
            download_url = cloudinary.utils.cloudinary_url(
                public_id,
                resource_type=resource_type,
                type="upload",
                flags="attachment"
            )[0]
            
            # Создаем URL для предварительного просмотра (без флага attachment)
            preview_url = cloudinary.utils.cloudinary_url(
                public_id,
                resource_type=resource_type,
                type="upload",
                secure=True
            )[0]
            
            # Проверяем, существует ли колонка cloudinary_url в таблице albedo_file
            with connection.cursor() as cursor:
                try:
                    cursor.execute("SELECT cloudinary_url FROM albedo_file LIMIT 1")
                    has_cloudinary_url = True
                except Exception:
                    has_cloudinary_url = False
            
            # Возвращаем информацию о файле
            file_info = {
                'file_name': file.name,
                'safe_name': safe_filename,
                'file_path': public_id,
                'size': file.size,
                'mime_type': mime_type,
                'cloudinary_url': download_url,  # URL для скачивания
                'preview_url': preview_url       # URL для предварительного просмотра
            }
            
            return file_info, None
            
        except Exception as e:
            errors.append(f"Ошибка при загрузке файла в облачное хранилище: {str(e)}")
            return None, errors
    else:
        # Загружаем файл локально
        try:
            # Создаем директорию, если она не существует
            local_dir = os.path.join(upload_dir, subdir)
            os.makedirs(local_dir, exist_ok=True)
            
            file_path = os.path.join(local_dir, safe_filename)
            relative_path = os.path.join(os.path.basename(upload_dir), subdir, safe_filename)
            
            # Сохраняем файл
            with open(file_path, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)
            
            # Возвращаем информацию о файле
            file_info = {
                'file_name': file.name,
                'safe_name': safe_filename,
                'file_path': relative_path,
                'size': file.size,
                'mime_type': mime_type
            }
            
            return file_info, None
            
        except Exception as e:
            errors.append(f"Ошибка при сохранении файла: {str(e)}")
            return None, errors
