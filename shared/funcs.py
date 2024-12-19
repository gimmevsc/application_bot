import aiohttp
import random
import phonenumbers
import re
import json
import sqlite3
import tldextract
from datetime import datetime
from urllib.parse import quote

from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from random_user_agent.user_agent import UserAgent
from random_user_agent.params import OperatingSystem, SoftwareType, Popularity

from .callbacks import ProxyEditingCallbackData
from .enums import EUserStatus
from .keyboards import (
    demo_duration_keyboard,
    admin_duration_keyboard,
    start_keyboard,
    admin_start_keyboard,
)
from .data import demo_names, unlim_names, admin_names, max_names, operators
from .config import (
    USERS_FILE,
    PROXIES_FILE,
    logger,
    COUNTRY_CODES,
    PROXY_PATTERN,
    URL_PATTERN,
    PROXY_ATTEMPTS,
)

# Параметри випадкових User Agents
software_types = [SoftwareType.WEB_BROWSER.value]
popularity = [Popularity.POPULAR.value]
operating_systems = [
    OperatingSystem.WINDOWS.value,
    OperatingSystem.LINUX.value,
    OperatingSystem.MAC.value,
]
user_agent_rotator = UserAgent(
    software_types=software_types,
    operating_systems=operating_systems,
    popularity=popularity,
    limit=50,
)


# Функція для визначення імені відповідно до статусу користувача
def generate_name(user_id):
    # user_status = get_user_status(user_id)  # Отримуємо статус користувача
    user_status = get_user_status_db(user_id)

    # Якщо статус користувача не знайдений, використовуємо статус 'demo'
    
    ## додав ще один статус
    if user_status is None:
        user_status = EUserStatus.DEMO

    if user_status == EUserStatus.DEMO:
        return random.choice(demo_names)
    elif user_status == EUserStatus.UNLIMITED:
        return random.choice(unlim_names)
    elif user_status == EUserStatus.MAX:
        return random.choice(max_names)
    elif user_status == EUserStatus.ADMIN:
        return random.choice(admin_names)
    else:
        # Якщо статус не вказаний або невідомий, використовується список для статусу demo
        return random.choice(demo_names)


# Функція для генерації українського номера телефону з кодом оператора
def generate_phone_number():
    operator_name = random.choice(list(operators.keys()))
    operator_code = random.choice(operators[operator_name])
    phone_number = phonenumbers.parse(
        f"+{COUNTRY_CODES['ua']}{operator_code}{random.randint(1000000, 9999999)}", None
    )
    return phonenumbers.format_number(
        phone_number, phonenumbers.PhoneNumberFormat.INTERNATIONAL
    )


# Функція для перевірки коректності URL
def is_valid_url(url):
    return re.match(URL_PATTERN, url) is not None


# Завантаження даних користувачів з JSON-файлу
# def load_users_data(filepath="users.json"):
#     try:
#         with open(filepath, "r") as file:
#             users_json = json.load(file)
#         return users_json
#     except FileNotFoundError:
#         return {}

def load_users_data_db(user_id, param):
    connection = sqlite3.connect("users.db")
    cur = connection.cursor()

    cur.execute(f'SELECT {param} FROM users WHERE user_id = ?', (user_id,))
    
    result = cur.fetchall()
    
    connection.close()
    
    return result[0]


def get_user_status_db(user_id):
    result = load_users_data_db(user_id, 'status')[0]
    return result


# def get_user_status(user_id):
#     users = load_users_data()
#     user_data = users.get(str(user_id))
#     if user_data:
#         return user_data.get("status")
#     return None


# Функція для визначення клавіатури
def get_start_keyboard_db(user_id):
    # users = load_users_data()  # Завантажуємо дані користувачів
    users_status = get_user_status_db(user_id)
    # if users.get(str(user_id), {}).get("status") == EUserStatus.ADMIN:
    if users_status == EUserStatus.ADMIN:
        return admin_start_keyboard
    return start_keyboard


# Функція для визначення клавіатури
# def get_start_keyboard(user_id):
#     users = load_users_data()  # Завантажуємо дані користувачів
#     if users.get(str(user_id), {}).get("status") == EUserStatus.ADMIN:
#         return admin_start_keyboard
#     return start_keyboard


# def get_duration_keyboard(user_id):
#     users = load_users_data()  # Завантажуємо дані користувачів
#     if users.get(str(user_id), {}).get("status") == EUserStatus.ADMIN:
#         return admin_duration_keyboard
#     return demo_duration_keyboard

def get_duration_keyboard_db(user_id):
    users_status = get_user_status_db(user_id)  # Завантажуємо дані користувачів
    if users_status == EUserStatus.ADMIN:
        return admin_duration_keyboard
    return demo_duration_keyboard

# def get_duration_keyboard_db(user_id):
#     users = load_users_data()  # Завантажуємо дані користувачів
#     if users.get(str(user_id), {}).get("status") == EUserStatus.ADMIN:
#         return admin_duration_keyboard
#     return demo_duration_keyboard


# Альтернативна асинхронна перевірка URL за допомогою aiohttp
async def is_valid_url_aiohttp(url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return response.status == 200
    except aiohttp.ClientError:
        return False


# Завантаження даних користувачів з файлу
def load_users():
    try:
        with open(USERS_FILE, "r") as file:
            users = json.load(file)
            return {int(user_id): user_data for user_id, user_data in users.items()}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


# Збереження даних користувачів до файлу
def save_users(users):
    with open(USERS_FILE, "w") as file:
        json.dump(users, file, indent=4)


def user_in_db(user_id):
    connection = sqlite3.connect('users.db')
    cur = connection.cursor()
    
    query = '''SELECT EXISTS (SELECT 1 FROM users WHERE user_id = ?)'''
    
    cur.execute(query, (user_id,))
    
    result = cur.fetchall()[0][0]
    
    cur.close()
    connection.close()

    return result



def update_user(user_id, param, value):
    connection = sqlite3.connect('users.db')
    cur = connection.cursor()
    
    query = f'UPDATE users SET {param} = ? WHERE user_id = ?;'
            
    cur.execute(query, (value, user_id,))
    connection.commit()
    
    cur.close()
    connection.close()



def update_applications(user_id, value):
    connection = sqlite3.connect('users.db')
    cur = connection.cursor()

    query = '''UPDATE users SET applications_sent = applications_sent + ? WHERE user_id = ?;'''

    cur.execute(query, (value, user_id))

    connection.commit()

    cur.close()
    connection.close()


# Ініціалізація користувачів
users = load_users()



# Додавання нового користувача
# def register_user(user_id):
#     if user_id not in users:
#         users[user_id] = {
#             "id": user_id,
#             "registration_date": str(datetime.now()),
#             "status": EUserStatus.DEMO,
#             "applications_sent": 0,
#             "applications_per_url": {},
#         }
#         save_users(users)


def register_user(user_id):
    connection = sqlite3.connect("users.db")
    cur = connection.cursor()
    
    query = '''SELECT 1 FROM users WHERE user_id = ?'''
    
    cur.execute(query, (user_id,))
    
    exist = cur.fetchall()
    
    query = '''INSERT INTO users 
                (user_id, registration_date, status, applications_sent, applications_per_url)
                VALUES (?, ?, ?, ?, ?)'''
    if not exist:
        cur.execute(query, (str(user_id), str(datetime.now()), EUserStatus.DEMO, 0, 0))
        connection.commit()
    
    cur.close()
    connection.close()


def load_whitelists(user_id):
    connection = sqlite3.connect("users.db")
    cur = connection.cursor()

    query = '''SELECT domain FROM whitelist WHERE user_table_id = ?''' 

    cur.execute(query, (user_id,))
    
    result = cur.fetchall()
    
    cur.close()
    connection.close()
    
    return [item[0] for item in result]


def exist_domain(domain):
    connection = sqlite3.connect('users.db')
    cursor = connection.cursor()

    query = '''SELECT user_table_id FROM whitelist WHERE domain = ?'''
    cursor.execute(query, (domain,))

    result = cursor.fetchall()

    cursor.close()
    connection.close()
    
    return len(result) > 0

    
def add_whitelists(user_id, value):
    
    connection = sqlite3.connect("users.db")
    cur = connection.cursor()
    
    query = '''INSERT INTO whitelist (user_table_id, domain) VALUES (?, ?)'''
    
    cur.execute(query, (user_id, value,))
    connection.commit()
    
    cur.close()
    connection.close()
    
    
def remove_domain(user_id, domain):
    connection = sqlite3.connect("users.db")
    cur = connection.cursor()

    query = '''DELETE FROM whitelist WHERE domain = ? and user_table_id = ?''' 

    cur.execute(query, (domain, user_id,))
    
    connection.commit()
    
    cur.close()
    connection.close()
    

# Функція для отримання домену з URL
def extract_domain(url: str) -> str:
    extracted = tldextract.extract(url)
    domain = f"{extracted.domain}.{extracted.suffix}"
    return domain


# Функція для перевірки чи користувач досяг ліміту заявок
# def is_demo_limit_reached(user_id):
#     user_data = users.get(user_id, {})
#     return (
#         user_data.get("status") == EUserStatus.DEMO
#         and user_data.get("applications_sent", 0) >= 50
#     )

# Функція для перевірки чи користувач досяг ліміту заявок
def is_demo_limit_reached(user_id):
    return (
        get_user_status_db(user_id) == EUserStatus.DEMO
        and load_users_data_db(user_id, 'applications_sent') >= 50
    )


# Завантаження даних проксі у словник
def load_proxies():
    try:
        with open(PROXIES_FILE, "r") as file:
            proxies = json.load(file)
            # Перетворюємо об'єкт проксі на словник для зручного доступу за ім'ям
            return {name: proxy for name, proxy in proxies.get("proxies", {}).items()}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


# Завантаження даних проксі з json файлу
def open_proxy_json():
    try:
        with open(PROXIES_FILE, "r") as file:
            proxies = json.load(file)
            return proxies
    except (FileNotFoundError, json.JSONDecodeError):
        return {"proxies": {}}


def get_proxy_url(proxy_data: dict):
    url = f"http://{quote(proxy_data['login'])}:{quote(proxy_data['password'])}@{proxy_data['ip']}:{proxy_data['port']}"
    return url


# Функція для перевірки коректності введеного проксі
def is_valid_proxy(proxy):
    return re.match(PROXY_PATTERN, proxy) is not None


# Функція для генерації повідомлення про проксі з інформацією про його статус та налаштування.
def generate_proxy_message(proxy_id, proxy_data):
    status = "Ввімкнене" if proxy_data["use_proxy"] else "Вимкнене"
    return (
        f"Проксі {proxy_id}:\n"
        f"Статус: {status}\n"
        f"IP: {proxy_data['ip']}\n"
        f"Порт: {proxy_data['port']}\n"
        f"Логін: {proxy_data['login']}\n"
        f"Пароль: {proxy_data['password']}\n"
    )


# Функція для генерації інлайн-клавіатури для проксі з кнопками для управління статусом та редагуванням.
def generate_proxy_inline_keyboard(proxy_id, use_proxy):
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(
            text="Вимкнути" if use_proxy else "Ввімкнути",
            callback_data=ProxyEditingCallbackData(
                action="toggle", proxy_id=proxy_id
            ).pack(),
        ),
        InlineKeyboardButton(
            text="Редагувати",
            callback_data=ProxyEditingCallbackData(
                action="edit", proxy_id=proxy_id
            ).pack(),
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="Видалити дані",
            callback_data=ProxyEditingCallbackData(
                action="delete_data", proxy_id=proxy_id
            ).pack(),
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="Видалити проксі",
            callback_data=ProxyEditingCallbackData(
                action="delete_proxy", proxy_id=proxy_id
            ).pack(),
        )
    )
    return builder.as_markup()


# Функція для перевірки працездатності проксі за заданими параметрами.
async def is_proxy_working(
    ip,
    port,
    login,
    password,
    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/87.0.4280.88 Safari/537.36",
):
    proxy_url = f"http://{quote(login)}:{quote(password)}@{ip}:{port}"
    url = "https://checkip.amazonaws.com"  # Тестовый URL для перевiрки проксi
    # url = 'https://ifconfig.me/ip'
    # url = 'https://httpbin.org/ip'

    timeout = aiohttp.ClientTimeout(total=15)

    async with aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(ssl=False), timeout=timeout
    ) as session:
        try:
            headers = {"User-Agent": user_agent}
            # 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36'

            async with session.get(url, proxy=proxy_url, headers=headers) as response:

                if response.status == 200:
                    return True
                else:
                    logger.error(f"Returned status {response.status} for {proxy_url}")
                    return False
        except aiohttp.ClientError as e:
            logger.error(f"Client error with proxy {proxy_url}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error with proxy {proxy_url}: {str(e)}")
            return False


async def check_proxy(proxy, user_agent, proxies):
    for attempt in range(PROXY_ATTEMPTS):
        if await is_proxy_working(
            ip=proxy["ip"],
            port=proxy["port"],
            login=proxy["login"],
            password=proxy["password"],
            user_agent=user_agent,
        ):
            proxies.append(get_proxy_url(proxy))
            return
        else:
            logger.error(
                f"Проксі http://{proxy['login']}:{proxy['password']}@{proxy['ip']}:{proxy['port']} недоступне, спроба {attempt+1} з {PROXY_ATTEMPTS}"
            )


# Функція для підготовки повідомлень про проксі з інформацією та інлайн-клавіатурами.
async def prepare_proxy_messages(proxies_dict: dict) -> list:
    proxy_messages = []
    for proxy_id, proxy_data in proxies_dict.items():
        text = generate_proxy_message(proxy_id, proxy_data)
        keyboard = generate_proxy_inline_keyboard(proxy_id, proxy_data["use_proxy"])
        proxy_messages.append((text, keyboard))
    return proxy_messages


# Функція для оновлення данных проксi
def update_proxy_data(proxy_id, ip, port, login, password, proxies=None):
    if proxies is None:
        proxies = open_proxy_json()

    if proxy_id in proxies["proxies"]:
        proxies["proxies"][proxy_id]["ip"] = ip
        proxies["proxies"][proxy_id]["port"] = port
        proxies["proxies"][proxy_id]["login"] = login
        proxies["proxies"][proxy_id]["password"] = password

        with open(PROXIES_FILE, "w") as file:
            json.dump(proxies, file, indent=4)


# Функція для створення нового проксі
def insert_proxy_data(ip, port, login, password):
    proxies = open_proxy_json()

    proxy_id = "1"

    for proxy_id_int in range(1, len(proxies["proxies"]) + 2):
        if str(proxy_id_int) not in proxies["proxies"]:
            proxy_id = str(proxy_id_int)
            break

    proxies["proxies"][proxy_id] = {}
    proxies["proxies"][proxy_id]["use_proxy"] = False

    update_proxy_data(proxy_id, ip, port, login, password, proxies)
    return proxy_id


# Функція для перемикання стану використання проксі за вказаним ідентифікатором.
def toggle_proxy_state(proxy_id):
    proxies = open_proxy_json()
    if proxy_id in proxies["proxies"]:
        current_state = proxies["proxies"][proxy_id]["use_proxy"]
        new_state = not current_state

        proxies["proxies"][proxy_id]["use_proxy"] = new_state
        with open(PROXIES_FILE, "w") as file:
            json.dump(proxies, file, indent=4)


# Функція видалення даних з проксі
def delete_proxy_data(proxy_id):
    proxies = open_proxy_json()
    if proxy_id in proxies["proxies"]:
        proxies["proxies"][proxy_id]["ip"] = ""
        proxies["proxies"][proxy_id]["port"] = ""
        proxies["proxies"][proxy_id]["login"] = ""
        proxies["proxies"][proxy_id]["password"] = ""
        proxies["proxies"][proxy_id]["type"] = ""

        with open(PROXIES_FILE, "w") as file:
            json.dump(proxies, file, indent=4)


# Функція видалення проксі та новий порядок
def delete_proxy(proxy_id):
    data = open_proxy_json()

    if proxy_id in data["proxies"]:
        del data["proxies"][proxy_id]

    proxies = data["proxies"]
    keys = list(proxies.keys())
    for i in range(len(keys)):
        new_key = str(i + 1)
        proxies[new_key] = proxies.pop(keys[i])

    with open("proxies.json", "w") as file:
        json.dump(data, file, indent=4)


# Функція отримання випадкового User Agent
def get_user_agent():
    return user_agent_rotator.get_random_user_agent()
