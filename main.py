import telebot
import openai
from dotenv.main import load_dotenv
import json
import os
import datetime


DEFAULT_SYSTEM_PROMPT = "You are a helpful assistant."
PRICE_1K = 0.002  # price per 1k rokens in USD
DATE_FORMAT = "%d.%m.%Y %H:%M:%S"  # date format for logging


# load .env file with secrets
load_dotenv()

# Load OpenAI API credentials from .env file
openai.api_key = os.getenv("OPENAI_API_KEY")

# Create a new Telebot instance
bot = telebot.TeleBot(os.getenv("TELEGRAM_API_KEY"))

# Получаем айди админа, которому в лс будут приходить логи
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# File with users and global token usage data
DATAFILE = "data.json"


"""======================FUNCTIONS======================="""


# Function to check if the user is in the data file
def is_user_exists(user_id: int) -> bool:
    if user_id in data:
        return True
    else:
        return False


# Function to add new user to the data file
def add_new_user(user_id: int, name: str, username: str) -> None:
    data[user_id] = DEFAULT_DATA.copy()
    data[user_id]["name"] = name
    if username is not None:
        data[user_id]["username"] = '@'+username
    else:
        data[user_id]["username"] = "None"


# Function to update the JSON file with relevant data
def update_json_file(new_data) -> None:
    with open(DATAFILE, "w") as file:
        json.dump(new_data, file, indent=4)


# Function to get the user's prompt
def get_user_prompt(user_id: int) -> str:
    if data[user_id].get("prompt") is None:
        return DEFAULT_SYSTEM_PROMPT
    else:
        return str(data[user_id]["prompt"])


# Function to call the OpenAI API and get the response
def call_chatgpt(user_request: str, prev_answer=None, system_prompt=DEFAULT_SYSTEM_PROMPT):
    messages = [{"role": "system", "content": system_prompt}]

    if prev_answer is not None:
        messages.extend([{"role": "assistant", "content": prev_answer},
                         {"role": "user", "content": user_request}])
        print("\nЗапрос с контекстом 🤩")
    else:
        messages.append({"role": "user", "content": user_request})
        print("\nЗапрос без контекста")

    return openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        max_tokens=3000,
        messages=messages
    )


"""========================SETUP========================="""


# Check if the file exists
if os.path.isfile(DATAFILE):
    # Read the contents of the file
    with open(DATAFILE, "r") as f:
        data = json.load(f)

    # Convert keys to integers (except for the first key)
    for key in list(data.keys())[1:]:
        data[int(key)] = data.pop(key)
else:
    data = {"global": {"requests": 0, "tokens": 0},
            ADMIN_ID: {"requests": 0, "tokens": 0, "balance": 777777, "lastdate": "01-05-2023 00:00:00"}}
    # Create the file with default values
    update_json_file(data)

# Default values for new users, who are not in the data file
DEFAULT_DATA = {"requests": 0, "tokens": 0, "balance": 30000,
                "name": "None", "username": "None", "lastdate": "11-09-2001 00:00:00"}


# Calculate the price per token in cents
PRICE_CENTS = PRICE_1K / 10

# Session token and request counters
session_tokens, request_number = 0, 0


"""=======================HANDLERS======================="""


# Define the handler for the /start command
@bot.message_handler(commands=["start"])
def handle_start_command(message):
    user = message.from_user

    # Если юзер уже есть в базе, то просто здороваемся и выходим, иначе добавляем его в базу
    if is_user_exists(user.id):
        bot.send_message(message.chat.id, "Магдыч готов к работе 💪")  # мб выдавать случайное приветствие из пула
        return
    else:
        add_new_user(user.id, user.first_name, user.username)
        update_json_file(data)

        welcome_string = f"{user.first_name}, с подключением 🤝\n\n" \
                         f"На твой баланс зачислено 30к токенов 🤑\n\n" \
                         f"Полезные команды:\n/help - список команд\n/balance - баланс токенов\n" \
                         f"/stats - статистика запросов\n/prompt - установить системный промпт\n"
        bot.send_message(message.chat.id, welcome_string)

        new_user_log = f"\nНовый пользователь: {user.full_name} " \
                       f"@{user.username} {user.id}"
        print(new_user_log)
        bot.send_message(ADMIN_ID, new_user_log)


# Define the handler for the /stop command
@bot.message_handler(commands=["stop"])
def handle_stop_command(message):
    if message.from_user.id == ADMIN_ID:
        bot.reply_to(message, "Stopping the script...")
        bot.stop_polling()
    else:
        bot.reply_to(message, "Только админ может останавливать бота")


# Define the handler for the /help command
@bot.message_handler(commands=["help"])
def handle_help_command(message):
    bot.reply_to(message, "Список доступных команд:\n\n"
                          "/start - регистрация в системе\n/help - список команд (вы здесь)\n\n"
                          "/balance - баланс токенов\n/stats - статистика запросов\n\n"
                          "/prompt - установить свой системный промпт\n"
                          "/reset_prompt - вернуть промпт по умолчанию\n")


# Define the handler for the /balance command
@bot.message_handler(commands=["balance"])
def handle_balance_command(message):
    user_id = message.from_user.id

    # Если юзер есть в базе, то выдаем его баланс, иначе просим его зарегистрироваться
    if is_user_exists(user_id):
        balance = data[user_id]["balance"]
        bot.reply_to(message, f"Ваш баланс: {balance} токенов")
    else:
        bot.reply_to(message, "Вы не зарегистрированы в системе. Напишите /start")


# Define the handler for the /stats command
@bot.message_handler(commands=["stats"])
def handle_stats_command(message):
    user_id = message.from_user.id

    # Если юзер есть в базе, то выдаем его статистику, иначе просим его зарегистрироваться
    if is_user_exists(user_id):
        user_stats = data[user_id]["requests"], data[user_id]["tokens"], data[user_id]["lastdate"]
        bot.reply_to(message, f"Запросов: {user_stats[0]}\n"
                              f"Токенов использовано: {user_stats[1]}\n"
                              f"Последний запрос: {user_stats[2]}")
    else:
        bot.reply_to(message, "Вы не зарегистрированы в системе. Напишите /start")


# Define the handler for the /prompt command
@bot.message_handler(commands=["prompt"])
def handle_prompt_command(message):
    user = message.from_user
    answer = ""

    prompt = message.text[len("/prompt"):].strip()

    # Если юзер есть в базе, то записываем промпт, иначе просим его зарегистрироваться
    if is_user_exists(user.id):
        if prompt:
            data[user.id]["prompt"] = prompt
            update_json_file(data)
            bot.reply_to(message, f"Установлен промпт: `{prompt}`", parse_mode="Markdown")
            print("\nУстановлен промпт: " + prompt)
        else:
            if "prompt" in data[user.id]:
                answer = f"*Текущий промпт:* `{str(data[user.id]['prompt'])}`\n\n"

            answer += "Системный промпт - это специальное указание, которое будет использоваться ботом вместе "\
                      "с каждым запросом для придания определенного поведения и стиля ответа. \n\n"\
                      "Для установки системного промпта напишите команду `/prompt`"\
                      " и требуемый текст одним сообщением, например: \n\n"\
                      "`/prompt Ты YodaGPT - AI модель, "\
                      "которая на все запросы отвечает в стиле Йоды из Star Wars`"

            bot.reply_to(message, answer,  parse_mode="Markdown")
            print("\nNo text provided.")
    else:
        bot.reply_to(message, "Вы не зарегистрированы в системе. Напишите /start")


# Define the handler for the /reset_prompt command
@bot.message_handler(commands=["reset_prompt"])
def handle_reset_prompt_command(message):
    user = message.from_user

    # Если юзер есть в базе, то сбрасываем промпт, иначе просим его зарегистрироваться
    if is_user_exists(user.id):
        if data[user.id].get("prompt") is not None:
            del data[user.id]["prompt"]
            update_json_file(data)
            bot.reply_to(message, f"Системный промпт сброшен до значения по умолчанию")
            print("\nСистемный промпт сброшен до значения по умолчанию")
        else:
            bot.reply_to(message, f"У вас уже стоит дефолтный промпт!")
            print("\nУ вас уже стоит дефолтный промпт!")
    else:
        bot.reply_to(message, "Вы не зарегистрированы в системе. Напишите /start")


# Define the message handler for incoming messages
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    global session_tokens, request_number, data
    user = message.from_user

    # Если юзер ответил на ответ боту другого юзера в групповом чате, то выходим, отвечать не нужно (issue #27)
    if message.reply_to_message is not None and message.reply_to_message.from_user.id != bot.get_me().id:
        print(f"\nUser {user.full_name} @{user.username} replied to another user, skip")
        return

    # Если пользователя нет в базе, то добавляем его с дефолтными значениями
    if not is_user_exists(user.id):
        add_new_user(user.id, user.first_name, user.username)

        new_user_string = f"\nНовый пользователь: {user.full_name} " \
                          f"@{user.username} {user.id}"
        print(new_user_string)
        bot.send_message(ADMIN_ID, new_user_string)

        # Записываем инфу о новом пользователе в файл
        update_json_file(data)

    # Проверяем, есть ли у пользователя токены на балансе
    if data[user.id]["balance"] <= 0:
        bot.reply_to(message, "У вас закончились токены. Пополните баланс")
        return

    # Send the user's message to OpenAI API and get the response
    # Если юзер написал запрос в ответ на сообщение бота, то добавляем предыдущий ответ бота в запрос
    try:
        if message.reply_to_message is not None and message.reply_to_message.from_user.id == bot.get_me().id:
            response = call_chatgpt(message.text, message.reply_to_message.text, get_user_prompt(user.id))
        else:
            response = call_chatgpt(message.text, system_prompt=get_user_prompt(user.id))
    except openai.error.RateLimitError:
        print("\nЛимит запросов!")
        bot.reply_to(message, "Превышен лимит запросов. Пожалуйста, повторите попытку позже")
        return

    # Получаем стоимость запроса по АПИ в токенах
    request_tokens = response["usage"]["total_tokens"]  # same: response.usage.total_tokens
    session_tokens += request_tokens
    request_number += 1

    # Обновляем глобальную статистику по количеству запросов и использованных токенов
    data["global"]["tokens"] += request_tokens
    data["global"]["requests"] += 1

    # Если юзер не админ, то списываем токены с баланса
    if user.id != ADMIN_ID:
        data[user.id]["balance"] -= request_tokens

    # Обновляем данные юзера по количеству запросов, использованных токенов и дате последнего запроса
    data[user.id]["tokens"] += request_tokens
    data[user.id]["requests"] += 1
    data[user.id]["lastdate"] = datetime.datetime.now().strftime(DATE_FORMAT)

    # Записываем инфу о количестве запросов и токенах в файл
    update_json_file(data)

    # Считаем стоимость запроса в центах
    request_price = request_tokens * PRICE_CENTS

    # формируем лог работы для юзера
    user_log = f"\n\n\nТокены: {request_tokens} за ¢{round(request_price, 3)} " \
               f"\nБип-боп"

    # Send the response back to the user
    if message.chat.type == "private":
        bot.send_message(message.chat.id, response.choices[0].message.content + user_log)
    else:
        bot.reply_to(message, response.choices[0].message.content + user_log)

    # Формируем лог работы для админа
    admin_log = (f"Запрос {request_number}: {request_tokens} за ¢{round(request_price, 3)}\n"
                 f"Сессия: {session_tokens} за ¢{round(session_tokens * PRICE_CENTS, 3)}\n"
                 f"Юзер: {user.full_name} "
                 f"@{user.username} {user.id}\n"
                 f"Чат: {message.chat.title} {message.chat.id}"
                 f"\n{data['global']} ¢{round(data['global']['tokens'] * PRICE_CENTS, 3)}")

    # Пишем лог работы в консоль
    print("\n" + admin_log)

    # Отправляем лог работы админу в тг
    if message.chat.id != ADMIN_ID:
        bot.send_message(ADMIN_ID, admin_log)


# Start the bot
print("---работаем---")
bot.infinity_polling()

# Уведомляем админа об успешном завершении работы
bot.send_message(ADMIN_ID, "Бот остановлен")
