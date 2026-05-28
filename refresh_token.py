import requests
import json
import os

def refresh_amocrm_token():
    subdomain = 'buqame'
    client_id = 'f4451ef5-0e39-4ebb-b5be-4942b014509f'
    client_secret = 'IMlDka8Igx7y2qbZsy4DlRkN70XSpMsBqD0RHs7pYaTqP8hCx8PLkUAIChGMWe1P'
    
    auth_code = 'def502004f19ff6a239329cf3c5eb41da61e783aa8e623ed0358da0f7a87b70e5f1b4dfd005e1bd7c0e4b596e6d1b6ee27cf00f54efe93deaa058747d2e6698f71b217e00a9d9a03a33430bc417d969b1579ed394c99579af35bb91050a8473ea2ab513ec59bf4658aa9a74a97c4ddb58e80b3acbded35b4d3d75498047c27b1a199ae00c48519522e34a7d0512b9b21be881708c28719586989f83032d751253e092d45a15a2e789c8c2c647fec1d43f80509816441470eff345a4d864c2250d96f1ea63e4978ff521ecf0167cab9b5cdb7b804f1055acdbfc5e2abe096cdfaa40764107b8519dd8d7cf3aef49d0b24c1efb152b382aa065d0dde2ffbfc65c6f8bb4f6a82c946c1816aa17f409b53db20addbfbba3dcfa3d6a362fab4f07c2156ceace128b695b25ff465c9f040e27fd2540d49f4fb26a70f6ae1b06aaa914fa02820923719094756b3be625198011f3ee5ddc879a52841e1ef87140f7498520ff45cd19286967b13db9685a1f52e0667503c50db676c797d963ce6cbc194b62b7d09dea610e997989be02eaad893816b90b2b2f7308295f53e72b73a000b06a18aa68a553f9ea094d8cfac1d733347035bd2eb802c72566832e811a387bae4e48a5f943e2382b38e664031a43c32beead940e6ca0e1cfb2ddfdabd37b4c488b2c90fe6afa53fd3adfca64dc44520367335c96a544929026d4397e4f0'
    
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
