import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def create_amocrm_lead(user_name, user_email, event_title=None, solution_data=None):
    subdomain = getattr(settings, 'AMOCRM_SUBDOMAIN', 'buqame')
    token = settings.AMOCRM_TOKEN
    
    base_url = f"https://{subdomain}.amocrm.ru/api/v4"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    contact_custom_fields = [
        {
            "field_code": "EMAIL",
            "values": [{"value": user_email, "enum_code": "WORK"}]
        }
    ]
    if event_title:
        contact_custom_fields.append({
            "field_id": 1359744,
            "values": [{"value": event_title}]
        })
            
    if solution_data:
        contact_custom_fields.append({
            "field_id": 1359746,
            "values": [{"enum_id": 1038186}]
        })

        contact_custom_fields.append({
            "field_id": 1359748,
            "values": [{"enum_id": 1038190}]
        })
            
        if 'created_at' in solution_data:
            import time
            contact_custom_fields.append({
                "field_id": 1359752,
                "values": [{"value": int(time.time())}]
            })
            
        if 'file_url' in solution_data:
            contact_custom_fields.append({
                "field_id": 1359754,
                "values": [{"value": solution_data['file_url']}]
            })

    contact_data = [
        {
            "name": user_name,
            "custom_fields_values": contact_custom_fields
        }
    ]

    try:
        contact_response = requests.post(f"{base_url}/contacts", headers=headers, json=contact_data)
        contact_response.raise_for_status()
        contact_id = contact_response.json().get('_embedded', {}).get('contacts', [{}])[0].get('id')
        
        lead_name = f"Решение: {event_title or 'Без названия'} ({user_name})"
        
        lead_data = [
            {
                "name": lead_name,
                "_embedded": {
                    "contacts": [{"id": contact_id}]
                }
            }
        ]
        
        lead_response = requests.post(f"{base_url}/leads", headers=headers, json=lead_data)
        lead_response.raise_for_status()
        
        return True
    except Exception as e:
        logger.error(f"Error creating amoCRM lead: {e}")
        if 'contact_response' in locals() and contact_response.status_code != 200:
            logger.error(f"Contact Response Error: {contact_response.text}")
        if 'lead_response' in locals() and lead_response.status_code != 200:
            logger.error(f"Lead Response Error: {lead_response.text}")
        return False
