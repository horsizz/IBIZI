import requests
import json
import os

def refresh_amocrm_token():
    subdomain = 'buqame'
    client_id = 'f4451ef5-0e39-4ebb-b5be-4942b014509f'
    client_secret = 'IMlDka8Igx7y2qbZsy4DlRkN70XSpMsBqD0RHs7pYaTqP8hCx8PLkUAIChGMWe1P'
    
    auth_code = 'def502004e3299ec5c53e5b551d8844895e0e1182e8c48fb7ef8aa4bf1d993412cf6bdacb4c95287a51d09957b8fed43e4c89fd58fa1192ab9e82b318cf1950b4e978de67ef4ea0eaf1d85947872fbbe69e89e464cd87cf09df1b0b85d59438a9833e4a710a0fa1afe5905f282b7db2c2774e1c88b22585e1393719ef690730f835ab79e82d41dec87040e2ef3447daaa77d0c6829b94456b8f5ef457144cb5a6304e2f91333494e48c700bd4cd11e311848a064823405387ada03a434f8c7ae44587972d9ab667a4a9361173ec388208eb598b573fb569e0f589629450e1fd3e5ebcc6ba3d2c7b70cda0363e2cade90a6e1bd6ec491762bef4dc352d69f9aa208fc68f999e4d437ce3f0796c1c74a065087edc80aa5bf4ca3d8a3d664185eb40d397802e832821847f7229ebd3e3428a09a2b9c3c675c946e0ff50f345f07c0184d20a61ff884f7b03a13e62ac8cfc3a4e294202ded3a277341780fc0c7408dcf5cf93b9da435596e5fc67e896244360987c8002c89047155a88c434b7654c9b82a457900784f28a23c7ac416a4ca0b113e974c494943c398de8088b4778764a1f62e6c8c3c336c1d42b74be2c15850ea9647c1a7edd0d44a35d1af4983a041ef94117ead1c6c76d58537deeb9a571167801607412bffbbfd632f4f21d5d9b2e4624503eef62cd419710d7c118c0f28bc49b53123b526063d6f79ccca'
    
    url = 'https://buqame.amocrm.ru/oauth2/access_token'
    
    data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'authorization_code',
        'code': auth_code.strip(),
        'redirect_uri': 'https://ibizi.onrender.com/amocrm/callback'
    }
    
    print('Запрос на получение нового токена...')
    response = requests.post(url, json=data)
    
    if response.status_code == 200:
        tokens = response.json()
        print('Успех! Токен получен.')
        env_path = os.path.join(os.path.dirname(__file__), '.env')
        acc = tokens['access_token']
        ref = tokens['refresh_token']
        with open(env_path, 'w', encoding='utf-8') as f:
            f.write(f'AMOCRM_TOKEN={acc}\n')
            f.write(f'AMOCRM_REFRESH_TOKEN={ref}\n')
        print(f'Новый Access Token сохранен в .env')
    else:
        print(f'ОШИБКА: {response.status_code}')
        print(response.text)

if __name__ == "__main__":
    refresh_amocrm_token()
