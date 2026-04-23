import requests
from django.conf import settings
import logging
import time

logger = logging.getLogger(__name__)

def create_amocrm_lead(user_name, user_email, event_title=None, solution_data=None):
    """
    Создает или обновляет КОНТАКТ в amoCRM (раздел Списки).
    Сделки (Leads) НЕ создаются.
    """
    subdomain = getattr(settings, 'AMOCRM_SUBDOMAIN', 'buqame')
    token = settings.AMOCRM_TOKEN
    
    base_url = f"https://{subdomain}.amocrm.ru/api/v4"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "amoCRM-Python-Client/1.0"
    }

    # 1. Поиск существующего контакта по email, чтобы не плодить дубли
    contact_id = None
    try:
        search_res = requests.get(f"{base_url}/contacts?query={user_email}", headers=headers)
        if search_res.status_code == 200:
            contacts = search_res.json().get('_embedded', {}).get('contacts', [])
            if contacts:
                contact_id = contacts[0].get('id')
    except Exception as e:
        logger.error(f"amoCRM search error: {e}")

    # 2. Подготовка полей Контакта (ПР-05)
    # 1350591 - Email, 1359744 - Название ивента, 1359746 - Роль, 1359748 - Статус, 1359752 - Дата
    contact_fields = [
        {"field_id": 1350591, "values": [{"value": user_email, "enum_id": 1033329}]}, 
        {"field_id": 1359744, "values": [{"value": str(event_title or "Олимпиада")}]}, 
        {"field_id": 1359746, "values": [{"enum_id": 1038186}]}, 
        {"field_id": 1359748, "values": [{"enum_id": 1038190}]}, 
        {"field_id": 1359752, "values": [{"value": int(time.time())}]}
    ]
    
    if solution_data and solution_data.get('file_url'):
        contact_fields.append({"field_id": 1359754, "values": [{"value": str(solution_data['file_url'])}]})

    try:
        if contact_id:
            # Обновляем существующий контакт в Списках
            print(f"--- [AMOCRM] Обновление существующего контакта ID: {contact_id} для {user_email} ---")
            update_data = {"id": contact_id, "name": user_name, "custom_fields_values": contact_fields}
            res = requests.patch(f"{base_url}/contacts/{contact_id}", headers=headers, json=update_data)
            res.raise_for_status()
            print(f"--- [AMOCRM] Контакт {contact_id} успешно обновлен в Списках ---")
        else:
            # Создаем новый контакт в Списках
            print(f"--- [AMOCRM] Создание нового контакта для {user_email} ---")
            create_data = [{"name": user_name, "custom_fields_values": contact_fields}]
            res = requests.post(f"{base_url}/contacts", headers=headers, json=create_data)
            res.raise_for_status()
            new_contact_id = res.json()['_embedded']['contacts'][0]['id']
            print(f"--- [AMOCRM] Создан новый контакт в Списках, ID: {new_contact_id} ---")
        
        return True
    except Exception as e:
        logger.error(f"amoCRM Contact update/create failed: {e}")
        print(f"--- [AMOCRM ERROR] Ошибка при работе с API: {str(e)} ---")
        if 'res' in locals():
            print(f"--- [AMOCRM ERROR] Ответ сервера: {res.text} ---")
        return False
