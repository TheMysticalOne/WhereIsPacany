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

import openai

try:
    with open('aitoken') as token_file:
        openai.api_key = token_file.read()
except Exception as e:
    logger.error(f'{e}')
    exit(1)

model_engine = "text-davinci-003"

token = ''

db = peewee.SqliteDatabase('wip.db')


class BaseModel(Model):
    class Meta:
        database = db


class ChatModel(BaseModel):
    gid = peewee.IntegerField(unique=True, primary_key=True)
    use_openai = peewee.BooleanField(default=False)


class UserModel(BaseModel):
    uid = peewee.IntegerField(primary_key=True)
    uname = peewee.CharField()
    chat = peewee.ForeignKeyField(ChatModel)
    pidorstat = peewee.IntegerField(default=0)
    voicestat = peewee.IntegerField(default=0)


db.create_tables([UserModel, ChatModel])
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

logger.debug(
    wh_info.ip_address if wh_info.ip_address else "There's no ip address at webhook")


def get_or_create_user_model(telegram_user: telebot.types.User, chat: ChatModel) -> UserModel:
    user: UserModel = None

    try:
        user = UserModel.get(
            UserModel.chat == chat and UserModel.uid == telegram_user.id)
    except:
        user = UserModel.create(
            uid=telegram_user.id,
            chat=chat,
            uname=telegram_user.username if telegram_user.username else f"user:{telegram_user.first_name}",
            pidorstat=0,
            voicestat=0
        )
        db.commit()

    return user


def get_or_create_chat_model(telegram_chat: telebot.types.Chat) -> UserModel:
    chat: ChatModel = None

    try:
        chat = ChatModel.get(ChatModel.gid == telegram_chat.id)
    except:
        chat = ChatModel.create(
            gid=telegram_chat.id,
            use_openai=False
        )
        db.commit()

    return chat


def get_registered_users(chat: ChatModel) -> List[UserModel]:
    try:
        return [um for um in UserModel.select().where(UserModel.chat == chat)]
    except:
        return []


def get_tag(user: UserModel):
    if not user.uname.startswith('user:'):
        tag = f"@{user.uname}"
    else:
        uname = str(user.uname)
        tag = f"[{uname.replace('user:', '')}](tg://user?id={user.uid})"

    return tag


def name_is_valid(name: str) -> bool:
    with open('valid_names.txt', encoding='utf-8') as names:
        names = names.read()

        if name.lower() in names:
            return True

    return False


def reply_where_pacan(message: Message, name: str, use_openai: False):
    case = 'потерялся'
    prefix = 'Он'

    name = name.title()

    logger.info(f"Replying where pacan {name}")

    if use_openai:
        completion = openai.Completion.create(
            engine=model_engine,
            prompt=f"Предположи самое необычное место, где мог бы находиться {name}",
            max_tokens=128,
            temperature=0.8,
            top_p=1.0,
            frequency_penalty=0.5,
            presence_penalty=0.0
        )

        ai_reply = completion.choices[0].text
        reply_to(message, ai_reply)

    else:
        if not name_is_valid(name):
            reply_to(message, escape_string(f'Я не знаю, кто такой {name}'))
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

        reply_to(
            message, f'{prefix.strip().replace("{NAME}", name)} {case.strip()}')


def reply_to_voice(message: Message, use_openai: False):
    if use_openai:
        completion = openai.Completion.create(
            engine=model_engine,
            prompt="Скажи в грубой форме, что голосовое сообщение это плохо, как если бы ты был гопником",
            max_tokens=64,
            temperature=0.8,
            top_p=1.0,
            frequency_penalty=0.5,
            presence_penalty=0.0
        )

        ai_reply = completion.choices[0].text
        reply_to(message, ai_reply)

    else:
        with open('audio_responses.txt', encoding='utf-8') as responses_file:
            responses = responses_file.readlines()
            response = random.choice(responses)
            reply_to(message, response)

    user = get_or_create_user_model(message.from_user, message.chat)
    user.voicestat += 1
    user.save()


def generate_hoku() -> str:
    f = Faker("ru_RU")
    head = str(f.date_of_birth(None, 40, 100)) + \
        ". " + f.job() + ".\n" + f.name() + ".\n"
    return "\n".join([head] + [f.sentence(nb_words=4) for i in range(3)])


@bot.message_handler(commands=["hoku"])
def hoku(message: Message):
    send_message(message.chat, generate_hoku())


@bot.message_handler(commands=["all"])
def all(message: Message):
    chat = get_or_create_chat_model(message.chat)

    try:
        msg = ""
        registered = get_registered_users(chat)
        for user in registered:
            msg += f" {get_tag(user)}"
        msg += message.text
        send_message(message.chat, msg.replace(
            "/all", "").replace(f"@{bot.user.username}", ''))

    except:
        send_message(message.chat, "404.. Как сквозь землю провалился..")


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
        pass


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
        .replace(')', '\\)') \
        .replace('(', '\\(') \
        .replace('!', '\\!')


def async_send(chat: telebot.types.Chat, messages: List[str], delay: int = 1):
    def _send(chat_: telebot.types.Chat, messages_: List[str], delay_: int = 1):
        for message in messages_:
            bot.send_message(chat_.id, escape_string(message))
            sleep(delay_)

    th = threading.Thread(target=_send, args=[chat, messages, delay])
    th.daemon = True
    th.start()


def send_message(chat: telebot.types.Chat, message: str):
    escaped = escape_string(message)
    logger.info(f"Sending message to {chat.id}: {escaped}")
    bot.send_message(chat.id, escape_string(message))


def reply_to(msg: telebot.types.Message, message: str):
    escaped = escape_string(message)
    logger.info(f"Sending reply to {msg.text}: {escaped}")
    bot.reply_to(msg, escaped)


@bot.message_handler(commands=["pidor"])
def who_is_pidor(message: Message):
    chat_model = get_or_create_chat_model(message.chat)

    try:
        registered = list(get_registered_users(chat_model))
        pidor_of_day = random.choice(registered)
        pidor_of_day.pidorstat += 1
        pidor_of_day.save()

        doubt_message = "Не может быть..."
        pidorcase_message = "Не может быть..."

        with open('doubts.txt', encoding='utf-8') as doubds:
            doubts_cases = doubds.readlines()
            doubt_message = random.choice(doubts_cases)

        with open('pidorcases.txt', encoding='utf-8') as pidorcases:
            pidor_cases = pidorcases.readlines()
            pidorcase_message = random.choice(pidor_cases)

        msg = f"{get_tag(pidor_of_day)}, ты - пидор."

        async_send(message.chat, [pidorcase_message,
                   doubt_message, msg.replace("/pidor", "")], 1)

    except Exception as e:
        send_message(message.chat, f"Ой, да вы все тут пидоры, потому что {e}")


@bot.message_handler(commands=["register"])
def register(message: Message):
    try:
        if message.from_user.is_bot:
            send_message(message.chat, "Не буду я ботов регать")
            return

        get_or_create_user_model(message.from_user, message.chat)

    except Exception as e:
        send_message(message.chat, f"Мда, что-то пошло не так: {e}")


@bot.message_handler(commands=["register_admins"])
def register(message: Message):
    chat_model = get_or_create_chat_model(message.chat)

    try:
        admins = bot.get_chat_administrators(message.chat.id)
        for admin in admins:
            if bot_uname == admin.user.username:
                admins.remove(admin)
                break

        for admin in admins:
            get_or_create_user_model(admin.user, chat_model)

        reply_to(message, "Готово!")

    except Exception as e:
        send_message(message.chat, f"Мда, что-то пошло не так: {e}")


@bot.message_handler(commands=["pidorstat"])
def pidorstat(message: Message):
    chat_model = get_or_create_chat_model(message.chat)

    try:
        msg = ""

        send_message(message.chat, "Секундочку.. сверяюсь с архивами...")

        q = UserModel.select().where(UserModel.chat == chat_model and UserModel.pidorstat != 0).order_by(
            UserModel.pidorstat.desc())

        if not q:
            send_message(message.chat, "В этом чате нет пидоров.")
            return

        pidors = [p for p in q]

        if not pidors:
            send_message(message.chat, "В этом чате нет пидоров.")
            return

        for user in pidors:
            user: UserModel

            msg += f"{get_tag(user)} {user.pidorstat}-кратный пидор\n"

        send_message(message.chat, msg)

    except Exception as e:
        send_message(message.chat, f"Ой, да вы все тут пидоры, потому что {e}")


def command_text(command: str, text: str) -> str:
    return text.lstrip(f"/{command}").strip()


@bot.message_handler(commands=["aimode"])
def voicestat(message: Message):
    chat_model = get_or_create_chat_model(message.chat)
    cmd = command_text("aimode", message.text)

    if cmd == "on":
        chat_model.use_openai = True
        send_message(
            message.chat, "Теперь я уже не тупая балванка, теперь я ИИ нахуй")
    elif cmd == "off":
        chat_model.use_openai = False
        send_message(message.chat, "Окей, теперь я тупая балванка")
    else:
        send_message(message.chat, "Я понимаю только on/off")

    chat_model.save()


def reply_handler(message: Message, use_ai: bool):
    try:
        if message.text:
            logger.info(f"Handle text {message.text}, AI: {use_ai}")
            with open('questions.txt', encoding='utf-8') as questions_file:
                questions = questions_file.readlines()
                for variant in questions:
                    txt = message.text.lower()
                    regex = variant.strip().replace("{NAME}", "(\\w+)")
                    name_found = re.findall(
                        fr'(?u){regex}', txt, re.IGNORECASE)

                    if name_found:
                        reply_where_pacan(message, name_found[0], use_ai)
                        return

        elif message.voice:
            logger.info(f"Handle voice openai, AI: {use_ai}")
            reply_to_voice(message, use_ai)
        else:
            send_message(message.chat, "Чел, ты какую-то херобору отправил")

    except Exception as e:
        send_message(
            message.chat, f"Мои агентам не удалось выяснить его местонахождение, потому что '{e}'")


@bot.message_handler(func=lambda message: True, content_types=["voice", "text"])
def gde_pacany_handler(message: Message):
    message_sender = message.from_user

    chat_model = get_or_create_chat_model(message.chat)

    if not message_sender.is_bot:
        get_or_create_user_model(message.from_user, chat_model)

    reply_handler(message, chat_model.use_openai)


bot.infinity_polling()
