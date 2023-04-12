import json
import os
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, request

import cms_api
import cache
from db import get_database_connection
from fb_utils import send_cart_menu, send_menu, send_message

app = Flask(__name__)


def handle_start(sender_id, message_text):
    send_menu(sender_id, category_slug=message_text, token=FACEBOOK_TOKEN)
    return "MENU"


def handle_menu(sender_id, message_text: str):
    if message_text == 'CART':
        client_cart = cms_api.get_cart(sender_id)
        send_cart_menu(sender_id, client_cart, token=FACEBOOK_TOKEN)
        return 'CART'

    if 'ADD_TO_CART' in message_text:
        _, product_id, product_name = message_text.split(':')
        cms_api.add_to_cart(sender_id, product_id, quantity=1)
        send_message(sender_id, f'В корзину добавлена пицца {product_name}', FACEBOOK_TOKEN)
    else:
        send_menu(sender_id, message_text, token=FACEBOOK_TOKEN)
    return "MENU"


def handle_cart(sender_id, message_text: str):
    if message_text == "MENU":
        send_menu(sender_id, category_slug="", token=FACEBOOK_TOKEN)
        return "MENU"

    if "ADD_TO_CART" in message_text:
        _, product_id, product_name = message_text.split(':')
        cms_api.add_to_cart(sender_id, product_id, quantity=1)
        send_message(sender_id, f'В корзину добавлена пицца {product_name}', FACEBOOK_TOKEN)

    elif "DELETE_FROM_CART" in message_text:
        _, product_id, product_name = message_text.split(':')
        cms_api.delete_from_cart(sender_id, product_id)
        send_message(sender_id, f'В Пицца {product_name} удалена из корзины', FACEBOOK_TOKEN)

    client_cart = cms_api.get_cart(sender_id)
    send_cart_menu(sender_id, client_cart, token=FACEBOOK_TOKEN)
    return "CART"


def handle_users_reply(sender_id, message_text):
    states_functions = {
        "START": handle_start,
        "MENU": handle_menu,
        "CART": handle_cart,
    }
    recorded_state = db.get(f'facebookid_{sender_id}')
    if not recorded_state or recorded_state not in states_functions.keys():
        user_state = "START"
    else:
        user_state = recorded_state
    if message_text == "":
        user_state = "START"
    state_handler = states_functions[user_state]
    next_state = state_handler(sender_id, message_text)
    db.set(f'facebookid_{sender_id}', next_state)


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
                    message_text = ""

                if messaging_event.get("postback"):
                    sender_id = messaging_event["sender"]["id"]
                    message_text = messaging_event["postback"]["payload"]

                handle_users_reply(sender_id, message_text)

    return "ok", 200


if __name__ == '__main__':
    load_dotenv()
    VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")
    FACEBOOK_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")
    db = get_database_connection()
    app.run(debug=True, port=5002)
