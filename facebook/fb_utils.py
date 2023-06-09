import json

import requests

import cms_api
from db import get_database_connection


def get_menu(category):
    client = get_database_connection()
    cached_menu = client.get(category)
    json_acceptable = cached_menu.replace("'", "\"")
    return json.loads(json_acceptable_string)


def send_message(recipient_id, message_text, token):
    params = {"access_token": token}
    headers = {"Content-Type": "application/json"}
    request_content = json.dumps({
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": message_text
        }
    })
    response = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers,
                             data=request_content)
    response.raise_for_status()

def send_menu(recipient_id, category_slug, token):
    if not category_slug:
        category_slug = 'front-page'
    send_main_menu(recipient_id, category_slug, token)


def create_menu_element(**menu):
    buttons = [
        {
            "type": "postback",
            "title": button["title"],
            "payload": button["payload"],
        }
        for button in menu["buttons"]
    ]

    return [
        {
            "title": menu["title"],
            "image_url": menu["image_url"],
            "subtitle": menu["subtitle"],
            "buttons": buttons
        }
    ]


def create_last_element(categories):
    buttons = [
        {
            "type": "postback",
            "title": category["name"],
            'payload': category["slug"],
        }
        for category in categories
    ]

    return [
        {
            "title": "Не нашли нужную пиццу?",
            "image_url": "https://primepizza.ru/uploads/position/large_0c07c6fd5c4dcadddaf4a2f1a2c218760b20c396.jpg",
            "subtitle": "Остальные пиццы можно посмотреть в одной из категорий",
            "buttons": buttons
        }
    ]


def send_template(recipient_id, elements, token):
    params = {"access_token": token}
    headers = {"Content-Type": "application/json"}
    request_content = {
        'recipient': {
            'id': recipient_id,
        },
        'message': {
            'attachment': {
                'type': 'template',
                'payload': {
                    'template_type': 'generic',
                    'elements': elements
                },
            },
        },
    }
    response = requests.post(
        "https://graph.facebook.com/v2.6/me/messages",
        params=params, headers=headers, json=request_content

    )
    response.raise_for_status()

def send_main_menu(recipient_id, category_slug, token):
    main_menu = {
        "title": "Меню",
        "image_url": "https://image.similarpng.com/very-thumbnail/2020/05/Pizza-logo-vector-PNG.png",
        "subtitle": "Здесь вы можете выбрать один из вариантов",
        "buttons": [
            {"title": "Корзина", "payload": "CART"},
            {"title": "Акции", "payload": "ACTION"},
            {"title": "Сделать заказ", "payload": "CHECKOUT"},
        ]
    }
    menu_element = create_menu_element(**main_menu)
    products = get_menu(category_slug)

    categories_without_start = cms_api.get_categories(category_exclude=category_slug)

    elements = [
        {
            "title": f'{product["name"]} ({product["price"]})',
            "image_url": product["image_path"],
            "subtitle": product["description"],
            "buttons": [
                {
                    'type': 'postback',
                    'title': 'Добавить в корзину',
                    'payload': f'ADD_TO_CART:{product["id"]}:{product["name"]}',
                },
            ],
        }
        for product in products["menu"]
    ]

    last_element = create_last_element(categories_without_start)

    elements = menu_element + elements + last_element
    send_template(recipient_id, elements, token)

def send_cart_menu(recipient_id, client_cart, token):
    basket_menu = {
        "title": f"Ваш заказ на сумму {client_cart['full_amount']} рублей",
        "image_url": "https://boniquet.com/wp-content/uploads/2019/01/grandesusperfiies.jpg",
        "subtitle": "",
        "buttons": [
            {"title": "Самовывоз", "payload": "PICKUP"},
            {"title": "Доставка", "payload": "DELIEVERY"},
            {"title": "В меню", "payload": "MENU"},
        ]
    }

    menu_element = create_menu_element(**basket_menu)
    products = client_cart["cart_items"]

    products_with_details = []
    for product in products:
        product_with_details = cms_api.get_product(product_id=product["product_id"])
        product_with_details["items_id"] = product["id"]
        products_with_details.append(product_with_details)


    elements = [
        {
            "title": f'{product["name"]} ({product["price"]})',
            "image_url": product["image_path"],
            "subtitle": product["description"],
            "buttons": [
                {
                    'type': 'postback',
                    'title': 'Добавить еще одну',
                    'payload': f'ADD_TO_CART:{product["id"]}:{product["name"]}',
                },
                {
                    'type': 'postback',
                    'title': 'Убрать из корзины',
                    'payload': f'DELETE_FROM_CART:{product["items_id"]}:{product["name"]}',
                },

            ],
        }
        for product in products_with_details
    ]

    elements = menu_element + elements
    send_template(recipient_id, elements, token)