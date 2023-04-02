import logging
import os

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler, PreCheckoutQueryHandler
from telegram.ext import Filters, Updater

import cms_api
import payment
from utils import create_keyboard_with_columns, fetch_coordinates, generate_cart, get_database_connection, \
    get_min_distance


def start(bot, update, job_queue):
    products = cms_api.get_products()
    reply_markup = InlineKeyboardMarkup(create_keyboard_with_columns(products, 3))

    if update.message:
        update.message.reply_text(text="Выберите свою пиццу:", reply_markup=reply_markup)
    else:
        update.callback_query.message.reply_text(text="Выберите свою пиццу:", reply_markup=reply_markup)
        bot.delete_message(chat_id=update.callback_query.message.chat_id,
                           message_id=update.callback_query.message.message_id)
    return "HANDLE_MENU"


def handle_menu(bot, update, job_queue):
    query = update.callback_query

    if query.data == 'cart':
        handle_cart(bot, update, job_queue)
        return "HANDLE_CART"

    product = cms_api.get_product(product_id=query.data)
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


def handle_description(bot, update, job_queue):
    query = update.callback_query

    if query.data == 'back':
        start(bot, update, job_queue)
        return "HANDLE_MENU"

    chat_id = update.callback_query.message.chat_id

    _, product_id = query.data.split()
    cms_api.add_to_cart(chat_id, product_id, quantity=1)

    query.bot.answer_callback_query(update.callback_query.id, text='Товар добавлен в корзину!', show_alert=True)
    return "HANDLE_DESCRIPTION"


def handle_cart(bot, update, job_queue):
    query = update.callback_query

    if query.data == 'back':
        start(bot, update, job_queue)
        return "HANDLE_MENU"
    elif query.data.startswith('delete'):
        _, item_id = query.data.split(':')
        cart_id = query.message.chat_id
        cms_api.delete_from_cart(cart_id, item_id)
        generate_cart(update)
    elif 'pay' in query.data:
        _, full_amount = query.data.split(':')
        payment.start_without_shipping(bot, update, int(full_amount))
        return "WAITING_ADDRESS"

    message, reply_markup = generate_cart(bot, update)
    bot.send_message(text=message,
                     chat_id=update.callback_query.message.chat_id,
                     reply_markup=reply_markup)
    bot.delete_message(chat_id=update.callback_query.message.chat_id,
                       message_id=update.callback_query.message.message_id)
    return "HANDLE_CART"


def handle_waiting_address(bot, update, job_queue):
    message = update.message

    if message.text:
        current_pos = fetch_coordinates(address=message.text)
        if current_pos is None:
            bot.send_message(text='Не могу распознать этот адрес', chat_id=message.chat_id)
            return "WAITING_ADDRESS"
    else:
        current_pos = message.location.longitude, message.location.latitude

    address, (min_distanse, delieveryman_id) = get_min_distance(current_pos)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton('Доставка', callback_data=f'delivery:{current_pos}:{delieveryman_id}')],
        [InlineKeyboardButton('Самовывоз', callback_data=f'pickup')]
    ])

    if min_distanse < 0.5:
        message = (
            f'Может заберете пиццу из нашей пиццерии неподалеку? Она всего в {round(min_distanse, 2)} метрах от вас!'
            f'Вот ее адрес: {address}. \n\n А можем и бесплатно доставить, нам не сложно')
    elif min_distanse < 5:
        message = (f'Ближайшая пиццерия находится по адресу: {address}. '
                   f'Доставка будет стоить 100 рублей.  Доставляем или самовывоз?')
    elif min_distanse < 20:
        message = (f'Ближайшая пиццерия находится по адресу: {address}.'
                   f'Доставка авто будет стоить 300 рублей.  Доставляем или самовывоз?')
    elif min_distanse < 50:
        message = (f'Ближайшая пиццерия находится по адресу: {address}. '
                   f'К сожалению на такую дистанцию только самовывоз')
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Самовывоз", callback_data=f'pickup')]
        ])
    else:
        message = 'Так далеко мы не доставляем'
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("В меню", callback_data='back')]
        ])

    bot.send_message(text=message, chat_id=update.message.chat_id, reply_markup=keyboard)
    return "HANDLE_DELIEVERY"


def message_for_client(bot, job):
    reclama = os.environ.get('PROMOTIONAL_MESSAGE')
    problem_message = os.environ.get('PROBLEM_MESSAGE')
    message = f'''
        Приятного аппетита! {reclama}\n\n
        {problem_message}
    '''
    bot.send_message(chat_id=job.context, text=message)


def handle_delievery(bot, update, job_queue):
    query = update.callback_query

    if 'delivery' in query.data:
        _, client_pos, delieveryman_id = query.data.split(':')
        long, lat = tuple(map(float, client_pos[1:-1].split(',')))
        order_message, _ = generate_cart(bot, update)
        bot.send_message(text=order_message, chat_id=query.message.chat_id)
        bot.send_location(
            chat_id=delieveryman_id,
            longitude=long,
            latitude=lat,
            message=order_message)

    message = f'Спасибо за заказ, ждем вас в нашей пиццерии'

    job_queue.run_once(message_for_client, 60 * 60, context=query.message.chat_id)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("В меню", callback_data='back')]
    ])
    bot.send_message(text=message, chat_id=query.message.chat_id, reply_markup=keyboard)
    return "HANDLE_DESCRIPTION"


def handle_users_reply(bot, update, job_queue):
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
        'HANDLE_CART': handle_cart,
        'WAITING_ADDRESS': handle_waiting_address,
        'HANDLE_DELIEVERY': handle_delievery,
    }

    state_handler = states_functions[user_state]
    try:
        next_state = state_handler(bot, update, job_queue)
        db.set(chat_id, next_state)
    except Exception as err:
        print(err)


def error_callback(bot, update, error):
    try:
        logging.error(str(update))
        update.message.reply_text(text='Возникла ошибка!')
    except Exception as err:
        logging.critical(err)


if __name__ == '__main__':
    load_dotenv()
    token = os.environ.get("TELEGRAM_TOKEN")

    db = get_database_connection()
    updater = Updater(token)

    dispatcher = updater.dispatcher
    dispatcher.add_handler(
        CommandHandler('start', handle_users_reply, pass_job_queue=True)
    )
    dispatcher.add_handler(
        CallbackQueryHandler(handle_users_reply, pass_job_queue=True)
    )
    dispatcher.add_handler(
        MessageHandler(Filters.text | Filters.location, handle_users_reply, pass_job_queue=True)
    )
    dispatcher.add_handler(PreCheckoutQueryHandler(payment.precheckout_callback))
    dispatcher.add_handler(
        MessageHandler(Filters.successful_payment, payment.successful_payment_callback)
    )
    dispatcher.add_error_handler(error_callback)
    updater.start_polling()
