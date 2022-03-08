import random
import os
import re
import threading
from time import sleep
from typing import List

import peewee
from peewee import Model

import telebot

from telebot.types import Message
from loguru import logger

token = ''

db = peewee.SqliteDatabase('wip.db')


class BaseModel(Model):
    class Meta:
        database = db


class UserModel(BaseModel):
    uname = peewee.CharField()
    chat_id = peewee.IntegerField()
    pidorstat = peewee.IntegerField(default=0)


db.create_tables([UserModel])
db.connect(True)

try:
    with open('token') as token_file:
        token = token_file.read()
except Exception as e:
    logger.error(f'{e}')
    exit(1)

logger.debug(f'Loaded token: {token}')
logger.debug(f'CWD: {os.getcwd()}')

bot = telebot.TeleBot(token.strip())
bot_uname = bot.get_me().username

wh_info = bot.get_webhook_info()

logger.debug(wh_info.ip_address if wh_info.ip_address else "There's no ip address at webhook")


def get_user_model(telegram_user: telebot.types.ChatMember, chat: telebot.types.Chat) -> UserModel:
    user: UserModel = None

    try:
        user = UserModel.get(UserModel.chat_id == chat.id and UserModel.uname == telegram_user.user.username)
    except:
        user = UserModel.create(
            uname=telegram_user.user.username,
            chat_id=chat.id,
            pidorstat=0
        )
        db.commit()

    return user


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


def async_send(chat: telebot.types.Chat, messages: List[str], delay: int = 1):
    def _send(chat_: telebot.types.Chat, messages_: List[str], delay_: int = 1):
        for message in messages_:
            bot.send_message(chat_.id, message)
            sleep(delay_)

    th = threading.Thread(target=_send, args=[chat, messages, delay])
    th.daemon = True
    th.start()


@bot.message_handler(commands=["pidor"])
def who_is_pidor(message: Message):
    try:
        admins = bot.get_chat_administrators(message.chat.id)
        for admin in admins:
            if bot_uname == admin.user.username:
                admins.remove(admin)
                break

        pidor_of_day = random.choice(admins)

        pidor_user_model = get_user_model(pidor_of_day, message.chat)
        pidor_user_model.pidorstat += 1
        pidor_user_model.save()

        doubt_message = "Не может быть..."
        pidorcase_message = "Не может быть..."

        with open('doubts.txt', encoding='utf-8') as doubds:
            doubts_cases = doubds.readlines()
            doubt_message = random.choice(doubts_cases)

        with open('pidorcases.txt', encoding='utf-8') as pidorcases:
            pidor_cases = pidorcases.readlines()
            pidorcase_message = random.choice(pidor_cases)

        msg = f"@{pidor_of_day.user.username}, ты - пидор."

        async_send(message.chat, [pidorcase_message, doubt_message, msg.replace("/pidor", "")], 1)

    except Exception as e:
        bot.send_message(message.chat.id, f"Ой, да вы все тут пидоры, потому что {e}")


@bot.message_handler(commands=["pidorstat"])
def pidorstat(message: Message):
    try:
        msg = ""

        bot.send_message(message.chat.id, "Секундочку.. сверяюсь с архивами...")

        pidors = list(
            UserModel.select().where(UserModel.chat_id == message.chat.id).order_by(UserModel.pidorstat.desc()))

        if not pidors:
            bot.send_message(message.chat.id, "В этом чате нет пидоров.")
            return

        for user in pidors:
            user: UserModel

            msg += f"@{user.uname} {user.pidorstat}-кратный пидор\n"

        bot.send_message(message.chat.id, msg)

    except Exception as e:
        bot.send_message(message.chat.id, f"Ой, да вы все тут пидоры, потому что {e}")


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
