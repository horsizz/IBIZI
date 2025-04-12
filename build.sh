#!/usr/bin/env bash
# exit on error
set -o errexit

# Установка зависимостей Python
pip install -r requirements.txt

# Сбор статических файлов
python manage.py collectstatic --no-input

# Применение миграций базы данных
python manage.py migrate

# Создание суперпользователя (только при первом деплое)
echo "from albedo.models import User; User.objects.create_superuser('Lider', 'admin@example.com', 'dimadimadima') if not User.objects.filter(username='Lider').exists() else None" | python manage.py shell

