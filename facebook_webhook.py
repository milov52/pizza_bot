import os

import requests
from dotenv import load_dotenv
from flask import Flask, request

import cms_api

app = Flask(__name__)


@app.route('/', methods=['GET'])
def verify():
    """
    При верификации вебхука у Facebook он отправит запрос на этот адрес. На него нужно ответить VERIFY_TOKEN.
    """
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
        if not request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return "Verification token mismatch", 403
        return request.args["hub.challenge"], 200
    return 'Hello world', 200


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
                    message_text = messaging_event["message"]["text"]
                    send_menu(sender_id)
                    # send_message(sender_id, message_text)
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


def send_menu(recipient_id):
    products = cms_api.get_products_by_category("front-page")
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

    elements = get_menu_element() + elements
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


def send_message(recipient_id, message_text):
    params = {"access_token": FACEBOOK_TOKEN}
    headers = {"Content-Type": "application/json"}
    request_content = {
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": message_text
        }
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
    # send_menu(123)

    app.run(debug=True, port=5002)
