import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

import cms_api

ADDRESSES_URL = 'https://dvmn.org/media/filer_public/90/90/9090ecbf-249f-42c7-8635-a96985268b88/addresses.json'
MENU_URl = 'https://dvmn.org/media/filer_public/a2/5a/a25a7cbd-541c-4caf-9bf9-70dcdf4a592e/menu.json'


def init_data():
    response_menu = requests.get(MENU_URl)
    response_menu.raise_for_status()
    products = response_menu.json()

    response_addresses = requests.get(ADDRESSES_URL)
    response_addresses.raise_for_status()
    addresses = response_addresses.json()

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


def create_keyboard_with_columns(products, columns_cnt: int):
    keyboard = []
    buttons = []

    for index, product in enumerate(products, start=1):
        buttons.append(InlineKeyboardButton(product["name"],
                                            callback_data=product["id"]))
        if index % columns_cnt == 0:
            keyboard.append(buttons)
            buttons = []
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
