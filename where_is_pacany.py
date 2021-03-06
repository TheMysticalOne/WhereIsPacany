import random
import os
import re
import threading
from time import sleep
from typing import List

import peewee
from faker import Faker
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
    user_id = peewee.IntegerField()
    chat_id = peewee.IntegerField()
    pidorstat = peewee.IntegerField(default=0)
    voicestat = peewee.IntegerField(default=0)


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

bot = telebot.TeleBot(token.strip(), parse_mode='MarkdownV2')
bot_uname = bot.get_me().username

wh_info = bot.get_webhook_info()

logger.debug(wh_info.ip_address if wh_info.ip_address else "There's no ip address at webhook")


def get_or_create_user_model(telegram_user: telebot.types.User, chat: telebot.types.Chat) -> UserModel:
    user: UserModel = None

    try:
        user = UserModel.get(UserModel.chat_id == chat.id and UserModel.user_id == telegram_user.id)
    except:
        user = UserModel.create(
            uname=telegram_user.username if telegram_user.username else f"user:{telegram_user.first_name}",
            chat_id=chat.id,
            user_id=telegram_user.id,
            pidorstat=0,
            voicestat=0
        )
        db.commit()

    return user


def get_or_create_user_model_by_creds(username: str, user_id: int, chat_id: str, chat: telebot.types.Chat) -> UserModel:
    user: UserModel = None

    try:
        user = UserModel.get(UserModel.chat_id == chat_id and UserModel.user_id == user_id)

    except:
        user = UserModel.create(
            uname=username,
            chat_id=chat.id,
            user_id=user_id,
            pidorstat=0,
            voicestat=0
        )
        db.commit()

    return user


def get_registered_users(chat: telebot.types.Chat) -> List[UserModel]:
    try:
        return [um for um in UserModel.select().where(UserModel.chat_id == chat.id)]
    except:
        return []


def get_tag(user: UserModel):
    if not user.uname.startswith('user:'):
        tag = f"@{user.uname}"
    else:
        uname = str(user.uname)
        tag = f"[{uname.replace('user:', '')}](tg://user?id={user.user_id})"

    return tag


def name_is_valid(name: str) -> bool:
    with open('valid_names.txt', encoding='utf-8') as names:
        names = names.read()

        if name.lower() in names:
            return True

    return False


def reply_where_pacan(message: Message, name: str):
    case = '??????????????????'
    prefix = '????'

    name = name.title()

    if not name_is_valid(name):
        reply_to(message, escape_string(f'?? ???? ????????, ?????? ?????????? {name}'))
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

    reply_to(message, f'{prefix.strip().replace("{NAME}", name)} {case.strip()}')


def generate_hoku() -> str:
    f = Faker("ru_RU")
    head = str(f.date_of_birth(None, 40, 100)) + ". " + f.job() + ".\n" + f.name()+".\n"
    return "\n".join([head] + [f.sentence(nb_words=4) for i in range(3)])


@bot.message_handler(commands=["hoku"])
def hoku(message: Message):
    logger.warning("asgasg")
    send_message(message.chat, generate_hoku())


@bot.message_handler(commands=["all"])
def all(message: Message):
    try:
        msg = ""
        registered = get_registered_users(message.chat)
        for user in registered:
            msg += f" {get_tag(user)}"
        msg += message.text
        send_message(message.chat, msg.replace("/all", "").replace(f"@{bot.user.username}", ''))

    except:
        send_message(message.chat, "404.. ?????? ???????????? ?????????? ????????????????????..")


@bot.message_handler(commands=["zaebat"])
def zaebat(message: Message):
    try:
        msg = ""
        name_found = re.findall(r'@[\w\d]+', message.text, re.IGNORECASE)
        if name_found:
            for i in range(10):
                send_message(message.chat, name_found[0])
            return
    except Exception as e:
        reply_where_pacan(message, f'???? ????????, ???????????? ?????? {e}')


def escape_string(string: str):
    return string.replace('_', '\\_') \
        .replace('*', '\\*') \
        .replace('~', '\\~') \
        .replace('`', '\\`') \
        .replace('>', '\\>') \
        .replace('#', '\\#') \
        .replace('+', '\\+') \
        .replace('-', '\\-') \
        .replace('=', '\\=') \
        .replace('|', '\\|') \
        .replace('{', '\\{') \
        .replace('}', '\\}') \
        .replace('.', '\\.') \
        .replace('!', '\\!')


def async_send(chat: telebot.types.Chat, messages: List[str], delay: int = 1):
    def _send(chat_: telebot.types.Chat, messages_: List[str], delay_: int = 1):
        for message in messages_:
            bot.send_message(chat_.id, escape_string(message))
            sleep(delay_)

    th = threading.Thread(target=_send, args=[chat, messages, delay])
    th.daemon = True
    th.start()


def send_message(chat: telebot.types.Chat, message):
    bot.send_message(chat.id, escape_string(message))


def reply_to(msg: telebot.types.Message, message):
    bot.reply_to(msg, escape_string(message))


@bot.message_handler(commands=["pidor"])
def who_is_pidor(message: Message):
    try:
        registered = list(get_registered_users(message.chat))
        pidor_of_day = random.choice(registered)
        pidor_of_day.pidorstat += 1
        pidor_of_day.save()

        doubt_message = "???? ?????????? ????????..."
        pidorcase_message = "???? ?????????? ????????..."

        with open('doubts.txt', encoding='utf-8') as doubds:
            doubts_cases = doubds.readlines()
            doubt_message = random.choice(doubts_cases)

        with open('pidorcases.txt', encoding='utf-8') as pidorcases:
            pidor_cases = pidorcases.readlines()
            pidorcase_message = random.choice(pidor_cases)

        msg = f"{get_tag(pidor_of_day)}, ???? - ??????????."

        async_send(message.chat, [pidorcase_message, doubt_message, msg.replace("/pidor", "")], 1)

    except Exception as e:
        send_message(message.chat, f"????, ???? ???? ?????? ?????? ????????????, ???????????? ?????? {e}")


@bot.message_handler(commands=["register"])
def register(message: Message):
    try:
        if message.from_user.is_bot:
            send_message(message.chat, "???? ???????? ?? ?????????? ????????????")
            return

        get_or_create_user_model(message.from_user, message.chat)

    except Exception as e:
        send_message(message.chat, f"??????, ??????-???? ?????????? ???? ??????: {e}")


@bot.message_handler(commands=["register_admins"])
def register(message: Message):
    try:
        admins = bot.get_chat_administrators(message.chat.id)
        for admin in admins:
            if bot_uname == admin.user.username:
                admins.remove(admin)
                break

        for admin in admins:
            get_or_create_user_model(admin.user, message.chat)

        reply_to(message, "????????????!")

    except Exception as e:
        send_message(message.chat, f"??????, ??????-???? ?????????? ???? ??????: {e}")


@bot.message_handler(commands=["pidorstat"])
def pidorstat(message: Message):
    try:
        msg = ""

        send_message(message.chat, "????????????????????.. ???????????????? ?? ????????????????...")

        q = UserModel.select().where(UserModel.chat_id == message.chat.id and UserModel.pidorstat != 0).order_by(
            UserModel.pidorstat.desc())

        if not q:
            send_message(message.chat, "?? ???????? ???????? ?????? ??????????????.")
            return

        pidors = [p for p in q]

        if not pidors:
            send_message(message.chat, "?? ???????? ???????? ?????? ??????????????.")
            return

        for user in pidors:
            user: UserModel

            msg += f"{get_tag(user)} {user.pidorstat}-?????????????? ??????????\n"

        send_message(message.chat, msg)

    except Exception as e:
        send_message(message.chat, f"????, ???? ???? ?????? ?????? ????????????, ???????????? ?????? {e}")


@bot.message_handler(commands=["voicestat"])
def voicestat(message: Message):
    try:
        msg = ""

        send_message(message.chat, "????????????????????.. ???????????????? ?? ????????????????...")

        q = UserModel.select().where(
            UserModel.chat_id == message.chat.id and UserModel.voicestat != 0).order_by(
            UserModel.voicestat.desc())

        voicewhores = [v for v in q]

        if not voicewhores:
            send_message(message.chat, "?? ???????? ???????? ?????? ??????????????????????.")
            return

        for user in voicewhores:
            user: UserModel

            msg += f"{get_tag(user)} {user.voicestat}-?????????????? ????????????????????\n"

        send_message(message.chat, msg)

    except Exception as e:
        send_message(message.chat, f"????, ???? ???? ?????? ?????? ????????????????????, ???????????? ?????? {e}")


@bot.message_handler(func=lambda message: True, content_types=["voice", "text"])
def gde_pacany_handler(message: Message):
    message_sender = message.from_user

    if message.from_user.is_bot:
        get_or_create_user_model(message.from_user, message.chat)

    try:
        if message.text:
            with open('questions.txt', encoding='utf-8') as questions_file:
                questions = questions_file.readlines()
                for variant in questions:
                    txt = message.text.lower()
                    regex = variant.strip().replace("{NAME}", "(\\w+)")
                    name_found = re.findall(fr'(?u){regex}', txt, re.IGNORECASE)
                    if name_found:
                        reply_where_pacan(message, name_found[0])
                        return
        elif message.voice:
            with open('audio_responses.txt', encoding='utf-8') as responses_file:
                responses = responses_file.readlines()
                response = random.choice(responses)
                reply_to(message, response)
                user = get_or_create_user_model(message_sender, message.chat)
                user.voicestat += 1
                user.save()
                return
        else:
            send_message(message.chat, "??????, ???? ??????????-???? ???????????????? ????????????????")
    except:
        send_message(message.chat, "?????????????? ???? ????????, ?????? ???? :(")


bot.infinity_polling()
