import random
import os
import re

import telebot

from telebot import types
from telebot.types import Message
from loguru import logger

token = ''

GROUP_ID = -1001188592066

with open('token') as token_file:
    token = token_file.read()

logger.debug(f'Loaded token: {token}')
logger.debug(f'CWD: {os.getcwd()}')

bot = telebot.TeleBot(token)

def name_is_valid(name: str) -> bool:
    with open('valid_names.txt', encoding='utf-8') as names:
        names = names.read()

        if name.lower() in names:
            return True

    return False


def reply_to(message: Message, name: str):
    case = 'потерялся'
    prefix = 'Он'

    name = name.title()

    if not name_is_valid(name):
        bot.reply_to(message, f'Я не знаю, кто такой {name}')
        return

    with open('cases.txt', encoding='utf-8') as cases_file:
        cases = cases_file.readlines()
        case = random.choice(cases)

    with open('prefix.txt', encoding='utf-8') as prefix_file:
        prefixes = prefix_file.readlines()
        prefix = random.choice(prefixes)

    bot.reply_to(message, f'{prefix.strip().replace("{NAME}", name)} {case.strip()}')


@bot.message_handler(commands=["loc"])
def locs(message: Message):
    try:
        for admin in bot.get_chat_administrators(message.chat.id):
            if admin.user.username == message.text.replace("/loc @", ""):
                keyboard = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
                button_geo = types.KeyboardButton(text="Я тут сука", request_location=True)
                keyboard.add(button_geo)
                bot.send_message(admin.user.id, "Ответь сука", reply_markup=keyboard)
    except:
        bot.send_message(message.chat.id, "SUKA YA NE MOGU NAYTI USERA V ADMINAH ILI ON MNE NE PISAL")


@bot.message_handler(content_types=["location"])
def forward(message):
    if message.location is not None:
        # bot.forward_message(to_chat_id, from_chat_id, message_id)
        bot.forward_message(GROUP_ID, message.chat.id, message.id)
        # logger.warning(message)
        # logger.debug(message.location)
        # logger.debug("latitude: %s; longitude: %s" % (message.location.latitude, message.location.longitude))


@bot.message_handler(func=lambda message: True)
def gde_pacany_handler(message: Message):
    try:
        with open('questions.txt', encoding='utf-8') as questions_file:
            questions = questions_file.readlines()
            for variant in questions:
                txt = message.text.lower()
                regex = variant.strip().replace("{NAME}", "(\\w+)")
                name_found = re.findall(fr'(?u){regex}', txt, re.IGNORECASE)
                if name_found:
                    reply_to(message, name_found[0])
                    return
    except:
        bot.send_message(message.chat.id, "DAZHE YA HUI ZHAET GDE ETOT EBLAN")


bot.infinity_polling()
