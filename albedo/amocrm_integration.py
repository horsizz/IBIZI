import requests
from django.conf import settings
import logging
import time
import os

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

    def refresh_access_token():
        """Попытаться обновить access token с помощью refresh token, если он есть в settings.
        Возвращает новый access_token или None.
        """
        # Try to populate missing AMOCRM_* settings from a local .env file (fallback)
        try:
            base = getattr(settings, 'BASE_DIR', None)
            if base:
                env_path = os.path.join(str(base), '.env')
                if os.path.exists(env_path):
                    with open(env_path, encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            if not line or line.startswith('#'):
                                continue
                            if '=' in line:
                                k, v = line.split('=', 1)
                                k = k.strip(); v = v.strip()
                                if k in ('AMOCRM_REFRESH_TOKEN', 'AMOCRM_CLIENT_SECRET', 'AMOCRM_TOKEN'):
                                    if not getattr(settings, k, None):
                                        try:
                                            setattr(settings, k, v)
                                        except Exception:
                                            pass
        except Exception:
            pass

        refresh_token = getattr(settings, 'AMOCRM_REFRESH_TOKEN', None)
        client_id = getattr(settings, 'AMOCRM_INTEGRATION_ID', None)
        client_secret = getattr(settings, 'AMOCRM_CLIENT_SECRET', None)
        if not (refresh_token and client_id and client_secret):
            logger.warning('amoCRM refresh token or client credentials missing')
            return None

        url = f"https://{subdomain}.amocrm.ru/oauth2/access_token"
        data = {
            'client_id': client_id,
            'client_secret': client_secret,
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'redirect_uri': getattr(settings, 'AMOCRM_REDIRECT_URI', 'https://ibizi.onrender.com/amocrm/callback')
        }
        try:
            r = requests.post(url, json=data, timeout=10)
            if r.status_code == 200:
                toks = r.json()
                new_access = toks.get('access_token')
                new_refresh = toks.get('refresh_token')
                # Попытаемся обновить settings для текущего процесса (не persist в Render)
                try:
                    settings.AMOCRM_TOKEN = new_access
                    if new_refresh:
                        settings.AMOCRM_REFRESH_TOKEN = new_refresh
                except Exception:
                    pass
                logger.info('amoCRM access token refreshed')
                return new_access
            else:
                logger.error('amoCRM refresh failed: %s %s', r.status_code, r.text)
        except Exception as e:
            logger.exception('amoCRM refresh exception: %s', e)
        return None

    # Вспомогательная функция для выполнения запроса с одной попыткой обновить токен при 401
    def send_request(method, url, headers=None, **kwargs):
        try:
            resp = requests.request(method, url, headers=headers, timeout=10, **kwargs)
        except Exception as e:
            logger.exception('amoCRM request exception: %s', e)
            raise

        if resp.status_code == 401:
            # Попытаться обновить токен и повторить один раз
            new_token = refresh_access_token()
            if new_token:
                headers = dict(headers or {})
                headers['Authorization'] = f"Bearer {new_token}"
                resp = requests.request(method, url, headers=headers, timeout=10, **kwargs)
        return resp


    
    contact_id = None
    # Ensure we have a valid access token before making the first request.
    # If there is no token but refresh credentials exist, try to refresh now.
    if not token:
        refreshed = refresh_access_token()
        if refreshed:
            token = refreshed
            headers['Authorization'] = f"Bearer {token}"
        else:
            logger.error('amoCRM access token missing and cannot refresh; skipping API calls')
            return False
    try:
        search_res = send_request('GET', f"{base_url}/contacts?query={user_email}", headers=headers)
        if search_res.status_code == 200:
            contacts = search_res.json().get('_embedded', {}).get('contacts', [])
            if contacts:
                contact_id = contacts[0].get('id')
        else:
            logger.debug('amoCRM search returned %s: %s', search_res.status_code, getattr(search_res, 'text', ''))
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
            res = send_request('PATCH', f"{base_url}/contacts/{contact_id}", headers=headers, json=update_data)
            res.raise_for_status()
            print(f"--- [AMOCRM] Контакт {contact_id} успешно обновлен в Списках ---")
        else:
            # Создаем новый контакт в Списках
            print(f"--- [AMOCRM] Создание нового контакта для {user_email} ---")
            create_data = [{"name": user_name, "custom_fields_values": contact_fields}]
            res = send_request('POST', f"{base_url}/contacts", headers=headers, json=create_data)
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