import os
from telegram import LabeledPrice
from dotenv import load_dotenv

load_dotenv()


def start_without_shipping(bot, update, price):
    chat_id = update.callback_query.message.chat.id
    title = f"Payment_{chat_id}"
    description = "Оплатите пиццу и мы сразу же начнем ее готовить"

    payload = f"Custom_Payload"
    provider_token = os.getenv('PAYMENT_TOKEN')
    start_parameter = f"Payment_{chat_id}"
    currency = "RUB"
    prices = [LabeledPrice("Test", price * 100)]
    bot.sendInvoice(chat_id, title, description, payload,
                    provider_token, start_parameter, currency, prices)


def precheckout_callback(bot, update):
    query = update.pre_checkout_query

    if query.invoice_payload != f"Custom_Payload":
        bot.answer_pre_checkout_query(pre_checkout_query_id=query.id, ok=False,
                                      error_message="Что то пошло не так")
    else:
        bot.answer_pre_checkout_query(pre_checkout_query_id=query.id, ok=True)


def successful_payment_callback(bot, update):
    update.message.reply_text("Пришлите нам Ваш адрес текстом или геолокацию.")