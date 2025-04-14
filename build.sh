#!/usr/bin/env bash
# exit on error
set -o errexit

# Установка зависимостей Python
pip install -r requirements.txt

# Очищаем папку staticfiles, если она существует
rm -rf staticfiles/

# Отладка: проверяем структуру до collectstatic
echo "=== Текущая директория и структура ==="
pwd
ls -la

# Отображаем настройки Django, связанные со статическими файлами
echo "=== Настройки Django для статических файлов ==="
python -c "from django.conf import settings; print('STATIC_ROOT:', settings.STATIC_ROOT); print('STATIC_URL:', settings.STATIC_URL); print('STATICFILES_DIRS:', settings.STATICFILES_DIRS); print('DEBUG:', settings.DEBUG)"

# Сбор статических файлов с подробным выводом
echo "=== Запуск collectstatic ==="
python manage.py collectstatic --no-input -v 2

# Проверяем содержимое папки staticfiles после сбора
echo "=== Содержимое папки staticfiles ==="
ls -la staticfiles/

# Применение миграций базы данных
python manage.py migrate
