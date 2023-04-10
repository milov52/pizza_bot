import os

import requests
from dotenv import load_dotenv
from flask import Flask, request
from db import get_database_connection

import cms_api

app = Flask(__name__)

def handle_start(sender_id, message_text):
    send_menu(sender_id, category_slug=message_text)
    return "START"

def handle_users_reply(sender_id, message_text):
    states_functions = {
        'START': handle_start,
    }
    recorded_state = db.get(sender_id)
    if not recorded_state or recorded_state.decode("utf-8") not in states_functions.keys():
        user_state = "START"
    else:
        user_state = recorded_state.decode("utf-8")
    if message_text == "/start":
        user_state = "START"
    state_handler = states_functions[user_state]
    next_state = state_handler(sender_id, message_text)
    db.set(f'faceobookid_{sender_id}', next_state)

@app.route('/', methods=['GET'])
def verify():
    """
    При верификации вебхука у Facebook он отправит запрос на этот адрес. На него нужно ответить VERIFY_TOKEN.
    """
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
        if not request.args.get("hub.verify_token") == os.environ["VERIFY_TOKEN"]:
            return "Verification token mismatch", 403
        return request.args["hub.challenge"], 200

    return "Hello world", 200

@app.route('/', methods=['POST'])
def webhook():
    """
    Основной вебхук, на который будут приходить сообщения от Facebook.
    """
    data = request.get_json()
    if data["object"] == "page":
        for entry in data["entry"]:
            for messaging_event in entry["messaging"]:
                if messaging_event.get("message"):
                    sender_id = messaging_event["sender"]["id"]
                    recipient_id = messaging_event["recipient"]["id"]
                    message_text = ''


                if messaging_event.get("postback"):
                    sender_id = messaging_event["sender"]["id"]
                    message_text = messaging_event["postback"]["payload"]

                handle_users_reply(sender_id, message_text)

    return "ok", 200


def get_menu_element():
    return [
        {
            "title": "Меню",
            "image_url": "https://image.similarpng.com/very-thumbnail/2020/05/Pizza-logo-vector-PNG.png",
            "subtitle": "Здесь вы можете выбрать один из вариантов",
            "buttons": [
                {
                    'type': 'postback',
                    'title': 'Корзина',
                    'payload': 'DEVELOPER_DEFINED_PAYLOAD',
                },
                {
                    'type': 'postback',
                    'title': 'Акции',
                    'payload': 'DEVELOPER_DEFINED_PAYLOAD',
                },
                {
                    'type': 'postback',
                    'title': 'Сделать заказ',
                    'payload': 'DEVELOPER_DEFINED_PAYLOAD',
                },
            ]
        }
    ]

def get_last_element(categories):
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


def send_menu(recipient_id, category_slug):
    if not category_slug:
        category_slug = 'front-page'

    products = cms_api.get_products_by_category(category_slug)
    categories_without_start = cms_api.get_categories(category_exclude=category_slug)
    last_element = get_last_element(categories_without_start)

    products_with_details = [cms_api.get_product(product_id=product["id"])
                             for product in products]

    params = {"access_token": FACEBOOK_TOKEN}
    headers = {"Content-Type": "application/json"}

    elements = [
        {
            "title": f'{product["name"]} ({product["price"]})',
            "image_url": product["image_path"],
            "subtitle": product["description"],
            "buttons": [
                {
                    'type': 'postback',
                    'title': 'Добавить в корзину',
                    'payload': 'DEVELOPER_DEFINED_PAYLOAD',
                },
            ],
        }
        for product in products_with_details
    ]

    elements = get_menu_element() + elements + last_element
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

if __name__ == '__main__':
    load_dotenv()
    VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")
    FACEBOOK_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")
    db = get_database_connection()
    # send_menu(123)
    app.run(debug=True, port=5002)
