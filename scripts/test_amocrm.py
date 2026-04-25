#!/usr/bin/env python3
import os
import requests
import json

SUBDOMAIN = os.getenv('AMOCRM_SUBDOMAIN', 'buqame')
CLIENT_ID = os.getenv('AMOCRM_INTEGRATION_ID')
CLIENT_SECRET = os.getenv('AMOCRM_CLIENT_SECRET')
ACCESS_TOKEN = os.getenv('AMOCRM_TOKEN')
REFRESH_TOKEN = os.getenv('AMOCRM_REFRESH_TOKEN')

BASE = f"https://{SUBDOMAIN}.amocrm.ru"

def refresh():
    if not (CLIENT_ID and CLIENT_SECRET and REFRESH_TOKEN):
        print('Missing CLIENT_ID/CLIENT_SECRET/REFRESH_TOKEN in environment; skipping refresh test')
        return None
    url = f"{BASE}/oauth2/access_token"
    payload = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'refresh_token',
        'refresh_token': REFRESH_TOKEN,
        'redirect_uri': os.getenv('AMOCRM_REDIRECT_URI', 'https://ibizi.onrender.com/amocrm/callback')
    }
    print('Requesting refresh token...')
    r = requests.post(url, json=payload, timeout=10)
    print('Status:', r.status_code)
    try:
        print(r.text)
        data = r.json()
        return data
    except Exception as e:
        print('Failed to parse response:', e)
        return None


def create_contact(name, email, token=None):
    token = token or ACCESS_TOKEN
    if not token:
        print('No ACCESS_TOKEN available; aborting create_contact')
        return
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    url = f"{BASE}/api/v4/contacts"
    payload = [{
        'name': name,
        'custom_fields_values': [
            {'field_id': 1350591, 'values': [{'value': email}]}
        ]
    }]
    print('Creating contact:', email)
    r = requests.post(url, headers=headers, json=payload, timeout=10)
    print('Status:', r.status_code)
    print(r.text)
    return r


if __name__ == '__main__':
    print('AMOCRM local tester')
    print('SUBDOMAIN=', SUBDOMAIN)
    # 1) Try refresh
    refreshed = refresh()
    if refreshed and 'access_token' in refreshed:
        new_token = refreshed['access_token']
        print('\nRefresh succeeded, new access token length:', len(new_token))
        # Optionally test create_contact with new token
        test_email = os.getenv('AMOCRM_TEST_EMAIL', 'test-local@example.com')
        create_contact('Test Local', test_email, token=new_token)
    else:
        print('\nRefresh failed or skipped. Trying create with existing AMOCRM_TOKEN from env...')
        if ACCESS_TOKEN:
            test_email = os.getenv('AMOCRM_TEST_EMAIL', 'test-local@example.com')
            create_contact('Test Local', test_email, token=ACCESS_TOKEN)
        else:
            print('No token available to test contact creation.')
