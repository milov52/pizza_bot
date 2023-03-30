import os
from functools import partial

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler
from telegram.ext import Filters, Updater

import cms_api
from utils import fetch_coordinates, get_database_connection, get_min_distance


def next_menu():
    pass


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


def start(bot, update, client_id):
    products = cms_api.get_products(client_id=client_id)
    reply_markup = InlineKeyboardMarkup(create_keyboard_with_columns(products, 3))

    if update.message:
        update.message.reply_text(text="Выберите свою пиццу:", reply_markup=reply_markup)
    else:
        update.callback_query.message.reply_text(text="Выберите свою пиццу:", reply_markup=reply_markup)
        bot.delete_message(chat_id=update.callback_query.message.chat_id,
                           message_id=update.callback_query.message.message_id)
    return "HANDLE_MENU"


def handle_menu(bot, update, client_id):
    query = update.callback_query

    if query.data == 'cart':
        view_cart(bot, update, client_id)
        return "HANDLE_CART"

    product = cms_api.get_product(product_id=query.data, client_id=client_id)
    image_path = product["image_path"]

    name = product["name"]
    description = product["description"]
    price = product["price"]

    detail = f'{name}\n\n Стоимость: {price}\n\n {description}'

    keyboard = [[InlineKeyboardButton("Назад", callback_data='back')],
                [InlineKeyboardButton('Положить в корзину', callback_data=f'add_to_cart {query.data}')]
                ]

    bot.send_photo(query.message.chat_id,
                   image_path,
                   caption=detail,
                   reply_markup=InlineKeyboardMarkup(keyboard))

    bot.delete_message(chat_id=update.callback_query.message.chat_id,
                       message_id=update.callback_query.message.message_id)

    return "HANDLE_DESCRIPTION"


def handle_description(bot, update, client_id):
    query = update.callback_query

    if query.data == 'back':
        start(bot, update, client_id)
        return "HANDLE_MENU"

    chat_id = update.callback_query.message.chat_id

    _, product_id = query.data.split()
    cms_api.add_to_cart(chat_id, product_id, 1, client_id)

    query.bot.answer_callback_query(update.callback_query.id, text='Товар добавлен в корзину!', show_alert=True)
    return "HANDLE_DESCRIPTION"


def view_cart(bot, update, client_id):
    query = update.callback_query

    if query.data == 'back':
        start(bot, update, client_id)
        return "HANDLE_MENU"
    elif query.data.startswith('delete'):
        _, item_id = query.data.split(':')
        cart_id = query.message.chat_id
        cms_api.delete_from_cart(cart_id, item_id, client_id)
        generate_cart(bot, update, client_id)
    elif query.data == 'pay':
        bot.send_message(text='Хорошо, пришлите нам ваш адрес текстом или геолокацию',
                         chat_id=update.callback_query.message.chat_id)
        return "WAITING_ADDRESS"

    message, reply_markup = generate_cart(bot, update, client_id)
    bot.send_message(text=message,
                     chat_id=update.callback_query.message.chat_id,
                     reply_markup=reply_markup)
    bot.delete_message(chat_id=update.callback_query.message.chat_id,
                       message_id=update.callback_query.message.message_id)
    return "HANDLE_CART"


def waiting_address(bot, update, client_id):
    message = update.message

    if message.text:
        current_pos = fetch_coordinates(address=message.text)
        if current_pos is None:
            bot.send_message(text='Не могу распознать этот адрес', chat_id=message.chat_id)
            return "WAITING_ADDRESS"
    else:
        current_pos = message.location.latitude, message.location.longitude

    address, min_distanse = get_min_distance(client_id, current_pos)

    keyboard = [[InlineKeyboardButton("Доставка", callback_data='delivery')],
                [InlineKeyboardButton('Самовывоз', callback_data='pickup')]
                ]

    if 0 < min_distanse <= 0.5:
        message = (f'Может заберете пиццу из нашей пиццерии неподалеку? Она всего в {round(min_distanse,2)} метрах от вас!'
                   f'Вот ее адрес: {address}. \n\n А можем и бесплатно доставить, нам не сложно')
    elif 0 < min_distanse <= 5:
        message = 'Похоже, придется ехать до вас на самокате. Доставка будет стоить 100 рублей.  Доставляем или самовывоз?'
    elif 5 < min_distanse <= 20:
        message = 'На самокате похоже не добраться. Доставка авто будет стоить 300 рублей.  Доставляем или самовывоз?'
    elif 20 < min_distanse <= 50:
        message = 'К сожалению на такую дистанцию только самовывоз'
    else:
        message = 'Так далеко мы не доставляем'

    keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("В меню", callback_data='back')]
        ])
    bot.send_message(text=message, chat_id=update.message.chat_id, reply_markup=keyboard)
    # bot.send_message(text=f'Ваш email: {email} сохранен',
    #                  chat_id=chat_id,
    #                  reply_markup=keyboard)
    # cms_api.create_user_account(str(chat_id), email, client_id)
    return "START"


def generate_cart(bot, update, client_id):
    chat_id = update.callback_query.message.chat_id
    cart_info = cms_api.get_cart(chat_id, client_id)
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
    buttons.append([InlineKeyboardButton("Оплатить", callback_data='pay')])

    reply_markup = InlineKeyboardMarkup(buttons)
    return message, reply_markup


def handle_users_reply(bot, update, client_id):
    if update.message:
        user_reply = update.message.text
        chat_id = update.message.chat_id
    elif update.callback_query:
        user_reply = update.callback_query.data
        chat_id = update.callback_query.message.chat_id
    else:
        return

    if user_reply == '/start':
        user_state = 'START'
    else:
        user_state = db.get(chat_id).decode('utf-8')

    states_functions = {
        'START': start,
        'HANDLE_MENU': handle_menu,
        'HANDLE_DESCRIPTION': handle_description,
        'HANDLE_CART': view_cart,
        'WAITING_ADDRESS': waiting_address,
    }

    state_handler = states_functions[user_state]
    try:
        next_state = state_handler(bot, update, client_id)
        db.set(chat_id, next_state)
    except Exception as err:
        print(err)


if __name__ == '__main__':
    load_dotenv()
    client_id = os.environ.get("CLIENT_ID")
    token = os.environ.get("TELEGRAM_TOKEN")

    # init_data(client_id)

    db = get_database_connection()

    updater = Updater(token)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler('start', partial(handle_users_reply, client_id=client_id)))
    dispatcher.add_handler(CallbackQueryHandler(partial(handle_users_reply, client_id=client_id)))
    dispatcher.add_handler(
        MessageHandler(Filters.text | Filters.location, partial(handle_users_reply, client_id=client_id)))

    updater.start_polling()
