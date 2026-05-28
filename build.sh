#!/bin/bash
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input

# Временно добавляем эту строку, чтобы исправить состояние БД
python manage.py migrate albedo 0005 --fake --no-input

python manage.py migrate --no-input