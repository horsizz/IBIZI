#!/bin/bash
# exit on error
set -o errexit

# Установка зависимостей Python
pip install -r requirements.txt

# Сбор статических файлов
python manage.py collectstatic --no-input

# Применение миграций базы данных
python manage.py migrate
