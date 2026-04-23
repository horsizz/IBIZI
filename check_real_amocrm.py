import os
import django
import sys

# Добавляем текущую директорию в путь, чтобы Django видел модули
sys.path.append(os.getcwd())

# Настройка окружения Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from albedo.amocrm_integration import create_amocrm_lead

print("\n--- ЗАПУСК РЕАЛЬНОЙ ПРОВЕРКИ amoCRM ---")
print("Используем настройки из config/settings.py")

# Пробуем создать контакт
test_email = "real_test_123@ibizi.ru"
result = create_amocrm_lead(
    user_name="Real Test User", 
    user_email=test_email, 
    event_title="Тестовый Ивент"
)

if result:
    print(f"\n✅ УСПЕХ! Теперь обнови страницу 'Списки -> Контакты' в amoCRM и найди {test_email}")
else:
    print("\n❌ ОШИБКА. Проверь вывод выше, там должна быть причина от сервера amoCRM.")
