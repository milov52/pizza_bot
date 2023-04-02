import os

import redis
import requests
from geopy import distance
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

import cms_api

ADDRESSES_URL = 'https://dvmn.org/media/filer_public/90/90/9090ecbf-249f-42c7-8635-a96985268b88/addresses.json'
MENU_URl = 'https://dvmn.org/media/filer_public/a2/5a/a25a7cbd-541c-4caf-9bf9-70dcdf4a592e/menu.json'

_database = None


def read_data(url: str):
    response = requests.get(url)
    return response.json()


def init_data():
    products = read_data(MENU_URl)
    addresses = read_data(ADDRESSES_URL)
    cms_api.get_addresses('Pizzeria')
    cms_api.create_product(products)

    cms_api.create_pizzeria_addresses_flow('Pizzeria')
    for address in addresses:
        address_data = {
            'data': {
                'type': 'entry',
                'address': address['address']['full'],
                'alias': address['alias'],
                'longitude': address['coordinates']['lon'],
                'latitude': address['coordinates']['lat']
            },
        }
        cms_api.add_addresses_to_flow(address_data, 'Pizzeria')


def fetch_coordinates(address):
    apikey = os.environ.get("API_YANDEX_GEO_KEY")
    base_url = "https://geocode-maps.yandex.ru/1.x"
    response = requests.get(base_url, params={
        "geocode": address,
        "apikey": apikey,
        "format": "json",
    })
    response.raise_for_status()
    found_places = response.json()['response']['GeoObjectCollection']['featureMember']

    if not found_places:
        return None

    most_relevant = found_places[0]
    lon, lat = most_relevant['GeoObject']['Point']['pos'].split(" ")
    return float(lon), float(lat)


def get_min_distance(current_pos):
    pizzerias_addresses = cms_api.get_addresses(flow_slug='Pizzeria')
    distances_to_pizzerias = {pizzerias_address['address']:
        (
            distance.distance(current_pos, pizzerias_address['coordinate']).km,
            pizzerias_address['telegram_id_delieveryman']
        )
        for pizzerias_address in pizzerias_addresses}

    min_distance = min(distances_to_pizzerias.items(), key=lambda x: x[1])
    return min_distance


def get_database_connection():
    global _database
    if _database is None:
        database_password = os.environ.get("DATABASE_PASSWORD")
        database_host = os.environ.get("DATABASE_HOST")
        database_port = os.environ.get("DATABASE_PORT")

        _database = redis.Redis(host=database_host, port=database_port, password=database_password)
    return _database


def create_keyboard_with_columns(products, columns_cnt: int):
    keyboard = []
    buttons = []

    for index, product in enumerate(products, start=1):
        buttons.append(InlineKeyboardButton(product["name"],
                                            callback_data=product["id"]))
        if index % columns_cnt == 0:
            keyboard.append(buttons)
            buttons = []

    # keyboard.append([InlineKeyboardButton('<<', callback_data=f'next {index+1}'),
    #                  InlineKeyboardButton('>>', callback_data=f'previous {index-6}')])
    keyboard.append([InlineKeyboardButton('Корзина',
                                          callback_data='cart')])
    return keyboard

def generate_cart(bot, update):
    chat_id = update.callback_query.message.chat_id
    cart_info = cms_api.get_cart(chat_id)
    message = ''
    buttons = []

    for item in cart_info["cart_items"]:
        message += f'{item["name"]}\n' \
                   f'{item["description"][:100]}\n' \
                   f'{item["quantity"]} пицц в корзине на сумму {item["amount"]}\n\n'

        buttons.append([InlineKeyboardButton(f'Убрать из корзины {item["name"]}',
                                             callback_data=f'delete:{item["id"]}')])

    message += f'К оплате: {cart_info["full_amount"]}'

    buttons.append([InlineKeyboardButton("В меню", callback_data='back')])
    buttons.append([InlineKeyboardButton("Оплатить", callback_data=f'pay:{cart_info["full_amount"]}')])

    reply_markup = InlineKeyboardMarkup(buttons)
    return message, reply_markup