from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

from shared.enums import EUserStatus
from .command_router import show_whitelist_menu, UserState
from shared.funcs import extract_domain, save_users, users, get_user_status_db, load_whitelists, remove_domain, add_whitelists


white_list_router = Router()


# Додавання доменів до вайтлиста
@white_list_router.message(lambda message: message.text == "📌 Додати домен")
async def request_domain(message: Message, state: FSMContext):
    user_id = message.from_user.id
    # user_data = users.get(user_id, {})
    user_domains = load_whitelists(user_id)
    # user_domains = user_data.get("whitelist", [])
    user_status = get_user_status_db(user_id)
    
    # Перевірка статусу користувача
    if user_status == EUserStatus.DEMO:
        return await message.answer(
            "❌ Ця функція доступна тільки у платній версії боту."
        )

    # Перевірка, чи користувач досяг ліміту на 3 домени
    if user_status == EUserStatus.DEMO and len(user_domains) >= 3:
        return await message.answer("❌ Ви не можете додати більше 3-х доменів.")

    # Перевірка, чи користувач досяг ліміту на 7 доменів
    if (user_status == EUserStatus.UNLIMITED or user_status == EUserStatus.MAX) and (len(user_domains) >= 7):
        return await message.answer("❌ Ви не можете додати більше 7-ми доменів.")

    await message.answer(
        "📩 Відправте посилання на сайт, домен якого ви хочете додати.",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="↩️ Повернутися назад")],
            ],
            resize_keyboard=True,
            one_time_keyboard=True,
        ),
    )
    await state.set_state(UserState.waiting_for_domain)


# Функція для обробки натискання на кнопку "Список доменів"
@white_list_router.message(lambda message: message.text == "📃 Список доменів")
async def list_domains(message: Message, state: FSMContext, user_id=None):
    # Ініціалізуємо ідентифікатор користувача
    user_id = user_id or message.from_user.id
    # user_domains = users.get(user_id, {}).get("whitelist", [])
    user_domains = load_whitelists(user_id)

    await state.set_state(UserState.domain_list)

    # Створюємо список кнопок
    domain_buttons = [[KeyboardButton(text=domain)] for domain in user_domains]
    domain_buttons.append([KeyboardButton(text="↩️ Повернутися назад")])

    domain_keyboard = ReplyKeyboardMarkup(
        keyboard=domain_buttons, resize_keyboard=True, one_time_keyboard=True
    )

    # Надсилаємо повідомлення залежно від наявності доменів
    if not user_domains:
        await message.answer(
            text="📋 Ваш вайтлист порожній.", reply_markup=domain_keyboard
        )
    else:
        await message.answer(
            text="Виберіть домен, який хочете видалити:", reply_markup=domain_keyboard
        )


# Функція для обробки натискання на домен в вайтлисті для видалення
@white_list_router.message( 
    lambda message: message.text
    in [domain for domain in load_whitelists(message.from_user.id)]
)
async def delete_domain(message: Message, state: FSMContext):
    user_id = message.from_user.id
    domain_to_remove = message.text

    # Видаляємо домен з вайтлиста
    if domain_to_remove in load_whitelists(user_id):
        
        remove_domain(user_id, domain_to_remove)
        # users[user_id]["whitelist"].remove(domain_to_remove)
        # save_users(users)
        
        await message.answer(f"✅ Домен {domain_to_remove} видалено з вайтлиста.")
    else:
        await message.answer("❌ Домен не знайдено у вашому вайтлисті.")

    # Повертаємось до списку доменів
    await list_domains(message, state)
    

# Функція для обробки натискання на кнопку "Додати домен"
@white_list_router.message(UserState.waiting_for_domain)
async def add_domain(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_domain = message.text

    # Отримуємо домен з URL
    domain = extract_domain(user_domain)

    # Додаємо домен до користувача
    # users[user_id]["whitelist"] = users[user_id].get("whitelist", [])
    
    if domain not in load_whitelists(user_id):
    
        add_whitelists(user_id, domain)
        # users[user_id]["whitelist"].append(domain)
        # save_users(users)  # Зберегти оновлення

        await message.answer(f"✅ Домен {domain} успішно додано до вайтлиста.")
    else:
        await message.answer("❌ Цей домен вже додано до вайтлиста.")

    # Повертаємося до меню вайтлиста
    await show_whitelist_menu(message, state)
