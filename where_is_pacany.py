import random
import os
import re

import telebot

from telebot.types import Message
from loguru import logger

token = ''

try:
    with open('token') as token_file:
        token = token_file.read()
except Exception as e:
    logger.error(f'{e}')
    exit(1)

logger.debug(f'Loaded token: {token}')
logger.debug(f'CWD: {os.getcwd()}')

bot = telebot.TeleBot(token.strip())

logger.debug(bot.get_webhook_info().ip_address)


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

    try:
        with open('cases.txt', encoding='utf-8') as cases_file:
            cases = cases_file.readlines()
            case = random.choice(cases)

        with open('prefix.txt', encoding='utf-8') as prefix_file:
            prefixes = prefix_file.readlines()
            prefix = random.choice(prefixes)

    except:
        pass

    bot.reply_to(message, f'{prefix.strip().replace("{NAME}", name)} {case.strip()}')


@bot.message_handler(commands=["all"])
def all(message: Message):
    try:
        bot_uname = bot.get_me().username
        msg = ""
        for admin in bot.get_chat_administrators(message.chat.id):
            if bot_uname != admin.user.username:
                msg += f" @{admin.user.username}"
        msg += message.text
        bot.send_message(message.chat.id, msg.replace("/all", ""))

    except:
        bot.send_message(message.chat.id, "404.. Как сквозь землю провалился..")

@bot.message_handler(commands=["zaebat"])
def zaebat(message: Message):
    try:
        msg = ""
        name_found = re.findall(r'@[\w\d]+', message.text, re.IGNORECASE)
        if name_found:
            for i in range(10):
                bot.send_message(message.chat.id, name_found[0])
            return
    except Exception as e:
        reply_to(message, f'Не буду, потому что {e}')



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
        bot.send_message(message.chat.id, "Понятия не имею, где он :(")


bot.infinity_polling()
