import os
import logging
import re
from dotenv import load_dotenv

# Define the path to the .env file
env_path = ".env"

# Load the environment variables from the .env file
load_dotenv(env_path)

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

USERS_FILE = "users.json"
PROXIES_FILE = "proxies.json"


def get_env_value(key):
    if key in os.environ:
        return os.environ[key]
    raise KeyError(f"Environment variable '{key}' not found")


API_TOKEN = get_env_value("API_TOKEN")
WEBHOOK_URL = get_env_value("WEBHOOK_URL")
__DEVELOPMENT = get_env_value("DEVELOPMENT")
DEVELOPMENT = __DEVELOPMENT == "True"

# Глобальні змінні для зберігання стану бота
user_state = {}
user_urls = {}
active_sessions = {}  # Активні сесії (посилання)
active_sending = {}  # Маркер активної відправки
active_tasks = {}  # Активні задачі
user_request_counter = {}
user_durations = {}  # Тривалість для кожного користувача
user_frequencies = {}  # Частота для кожного користувача
print(user_frequencies)

# Список вибору частоти відправки
frequency_options = [
    "Без затримки 🚀",
    "1 заявка в 10 секунд ⏳",
    "1 заявка в 10 хвилин ⌛",
    "1 заявка в 60 хвилин ⌛",
]

# Список вибору тривалості відправки
duration_options = [
    "1 хвилина ⏳",
    "15 хвилин ⏳",
    "30 хвилин ⏳",
    "1 година ⏳",
    "3 години ⏳",
    "Необмежено ⏳",
]


ATTEMPTS = 3  # Загальна кількість спроб
ATTEMPTS_USER_AGENTS = 2
PROXY_ATTEMPTS = 3  # Кількість спроб для кожного проксі
TIMEOUT = 15  # Таймаут для запитів
MAX_CONCURRENT_TASKS = 5


DURATION_MAPPING = {
    "1 хвилина ⏳": 60,
    "15 хвилин ⏳": 15 * 60,
    "30 хвилин ⏳": 30 * 60,
    "1 година ⏳": 60 * 60,
    "3 години ⏳": 3 * 60 * 60,
    "Необмежено ⏳": None,  # Необмежена тривалість
}

DELAY_MAPPING = {
    "Без затримки 🚀": 1,
    "1 заявка в 10 секунд ⏳": 10,
    "1 заявка в 10 хвилин ⌛": 600,
    "1 заявка в 60 хвилин ⌛": 3600,
}

COUNTRY_CODES = {"ua": 380}

PROXY_PATTERN = re.compile(
    r"^(?P<host>(?:\d{1,3}\.){3}\d{1,3}|(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}),"
    r"(?P<port>([1-9]\d{0,4}|[1-5]\d{5})),"
    r"(?P<username>[^\s,]+),"
    r"(?P<password>[^\s,]+)$"
)

URL_PATTERN = re.compile(
    r"^(?:http|ftp)s?://"
    r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|"
    r"localhost|"
    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
    r"\[?[A-F0-9]*:[A-F0-9:]+\]?)"
    r"(?::\d+)?"
    r"(?:/?|[/?]\S+)$",
    re.IGNORECASE,
)
