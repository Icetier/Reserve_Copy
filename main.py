from urllib.parse import urlencode
import pprint
import requests
import json
import configparser
from datetime import datetime
from tqdm import tqdm


class VK:
    api_base_url_vk = 'https://api.vk.com/method/'

    def __init__(self, token_vk, user_id, count, rev=True):
        self.token_vk = token_vk
        self.user_id = user_id
        self.count = count
        self.rev = rev

    def get_id_by_short_name(self, user_name):
        url = "https://api.vk.com/method/utils.resolveScreenName"
        params = {
            "access_token": token_vk,
            "v": "5.199",
            "screen_name": user_name
        }
        response = requests.get(url, params=params)
        if user_name.isdigit():
            return user_name
        else:
            return response.json()['response']['object_id']

    def get_profile_photos(self, album_id='profile'):
        params = {'access_token': self.token_vk,
                  'v': '5.199',
                  'extended': '1',
                  'count': self.count,
                  'rev': self.rev
                  }
        params.update({'user_id': self.user_id, 'album_id': album_id, 'count': self.count})
        response = requests.get(f'{self.api_base_url_vk}/photos.get?{urlencode(params)}')
        if isinstance(count, int) or int(count) <= 0:
            raise TypeError('Количество фотографий должно быть целым положительным числом')
        else:
            if 200 <= response.status_code < 300:
                print(f'Доступ к файлам есть, формируем список для резервного копирования')
                data = response.json()
                with open('response.json', 'w') as f:
                    json.dump(data, f, ensure_ascii=True, indent=2)
                photo_list = []
                likes_str = ''
                for idx, item in enumerate(data['response']['items']):
                    photo_list.append({'date': datetime.fromtimestamp(item['date']),
                                       'likes': item['likes']['count']})
                    likes_str += str(item['likes']['count']) + ' '
                    max_type = max_size(item['sizes'])
                    for size in item['sizes']:
                        if size['type'] == max_type:
                            photo_list[idx]['url'] = size['url']
                            photo_list[idx]['size'] = size['type']
                if len(photo_list) < int(count):
                    print(f'Будет скопировано лишь {len(photo_list)} фото из требуемых {count}!')
                    print(f'Причина: у пользователя ВСЕГО {len(photo_list)} фотографий!')
                sort_photo_list = sorted(photo_list, key=lambda x: x['likes'])
                for photo in sort_photo_list:
                    if likes_str.count(str(photo['likes'])) >= 1:
                        photo['file_name'] = f'{photo["likes"]}_{photo["date"].strftime("%m.%d.%y_%Hh%Mm%Ss")}.jpg'
                    else:
                        photo['file_name'] = f'{photo["likes"]}.jpg'
                return sort_photo_list


class YA:
    api_base_url_ya = 'https://cloud-api.yandex.net:443'

    def __init__(self, token_ya):
        self.token_ya = token_ya

    def check_folder_ya(self):
        headers = {'Authorization': self.token_ya}
        url = self.api_base_url_ya + '/v1/disk/resources'
        param = {'path': '/vk_photos'}
        response = requests.get(url, headers=headers, params=param)
        return response.status_code

    def make_folder_ya(self):
        headers = {'Authorization': self.token_ya}
        url = self.api_base_url_ya + '/v1/disk/resources'
        param = {'path': '/vk_photos'}
        response = requests.put(url, headers=headers, params=param)
        return response.status_code

    def photos_in_folder_ya(self):
        name_in_fold = []
        headers = {'Authorization': self.token_ya}
        url = self.api_base_url_ya + '/v1/disk/resources'
        param = {'path': '/vk_photos',
                 'limit': 1000000000000}
        response = requests.get(url, headers=headers, params=param)
        if 200 <= response.status_code < 300:
            data = response.json()
            for item in data['_embedded']['items']:
                name_in_fold.append(item['name'])
            return name_in_fold

    def upload_ya(self, file_list):
        result = self.check_folder_ya()
        if 200 <= result < 300:
            print(f'Папка есть, приступаем к резервному копированию')
            self.only_upload_ya(file_list)
        elif result == 404:
            response = self.make_folder_ya()
            if 200 <= response < 300:
                self.only_upload_ya(file_list)
        elif 400 <= result < 500:
            print(f'Проблема с программой')
        elif result >= 500:
            print(f'Проблема на стороне Яндекса')

    def only_upload_ya(self, file_list):
        name_in_fold = self.photos_in_folder_ya()
        headers = {'Authorization': self.token_ya}
        response_list = []
        if name_in_fold:
            for item in tqdm(file_list):
                if not (item['file_name'] in name_in_fold):
                    print(item['file_name'])
                    param = {'path': f'/vk_photos/{item["file_name"]}',
                             'url': item['url']}
                    url = self.api_base_url_ya + '/v1/disk/resources/upload'
                    response = requests.post(url, headers=headers, params=param)
                    response_list.append({'file_name': item['file_name'], 'code': response.status_code})
            bad_list = []
            for file in response_list:
                if not (200 <= file['code'] < 300):
                    bad_list.append(file['file_name'])
            if bad_list:
                print(f'При резервном копировании на Яндекс Диск произошла ошибка со следующими файлами:', end=' ')
                for file in bad_list:
                    print(file, end=' ')
            else:
                print(f'Резервное копирование на Яндекс Диск прошло успешно')
        else:
            for item in tqdm(file_list):
                param = {'path': f'/vk_photos/{item["file_name"]}',
                         'url': item['url']}
                url = self.api_base_url_ya + '/v1/disk/resources/upload'
                response = requests.post(url, headers=headers, params=param)
                response_list.append({'file_name': item['file_name'], 'code': response.status_code})
            bad_list = []
            for file in response_list:
                if not (200 <= file['code'] < 300):
                    bad_list.append(file['file_name'])
            if bad_list:
                print(f'При резервном копировании на Яндекс Диск произошла ошибка со следующими файлами:', end=' ')
                for file in bad_list:
                    print(file, end=' ')
            else:
                print(f'Резервное копирование на Яндекс Диск прошло успешно')


# region Max Size
def max_size(items: list):
    max_value = 0
    max_type = ''
    for item in items:
        if item['height'] * item['width'] >= max_value:
            max_value = item['height'] * item['width']
            max_type = item['type']
    return str(max_type)


# endregion

# region Getting Tokens From .ini
config = configparser.ConfigParser()
config.read("settings.ini")

token_vk = config['Vk']['token']
token_ya = config['Yandex']['token']
# print(config['Vk']['token'])
# print(config['Yandex']['token'])
# endregion

# region Input Data
f = input(f'Введите id или screen name для VK: ').strip()
user_id = VK.get_id_by_short_name(1, f)
count = input(f'Укажите количество фотографий: ').strip()

# endregion

# region Getting Photos From Profile
VK = VK(token_vk, user_id, count)
YA = YA(token_ya)
photo_list = VK.get_profile_photos()


# endregion

# region Required Lists
def json_upload():
    json_data = []
    upload_data = []

    for item in photo_list:
        json_data.append({'file_name': item['file_name'],
                          'size': item['size']})
        upload_data.append({'file_name': item['file_name'],
                            'url': item['url']})

    with open('files_list.json', 'w') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)
    with open('files_list.json') as f:
        f = json.load(f)
    print('Список фото:')
    pprint.pprint(f)
    return upload_data


# endregion

YA.upload_ya(json_upload())

# region Clean & Finish

open('response.json', 'w').close()
print(f'https://disk.yandex.ru/client/disk/vk_photos')

# endregion
