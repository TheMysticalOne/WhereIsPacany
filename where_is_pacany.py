import random
import re

import telebot
from telebot.types import Message

token = ''

with open('token') as token_file:
    token = token_file.read()

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


@bot.message_handler(func=lambda message: True)
def gde_ros(message: Message):
    with open('questions.txt', encoding='utf-8') as questions_file:
        questions = questions_file.readlines()
        for variant in questions:
            txt = message.text.lower()
            regex = variant.strip().replace("{NAME}", "(\\w+)")
            name_found = re.findall(fr'(?u){regex}', txt, re.IGNORECASE)
            if name_found:
                reply_to(message, name_found[0])
                return


bot.infinity_polling()
