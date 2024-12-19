import asyncio
from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
)
import time

from shared.enums import EUserStatus
from shared.task_manager import TaskManager
from .command_router import UserState
from shared.keyboards import frequency_keyboard, stop_keyboard, start_keyboard
from shared.funcs import (
    is_valid_url,
    update_applications,
    user_in_db,
    load_users_data_db,
    # get_start_keyboard,
    get_start_keyboard_db,
    exist_domain,
    # get_duration_keyboard,
    get_duration_keyboard_db,
    save_users,
    extract_domain,
    get_user_status_db,
    is_demo_limit_reached,
    users,
)
from shared.config import (
    active_sending,
    active_sessions,
    active_tasks,
    duration_options,
    logger,
    user_durations,
    user_request_counter,
    user_urls,
    user_frequencies,
    frequency_options,
    DURATION_MAPPING,
    DELAY_MAPPING,
)
from shared.send_request_to_form import send_request_to_form


request_router = Router()

task_manager = TaskManager()


# Обробник натискання інлайн кнопок відправки заявок
@request_router.callback_query(
    lambda callback_query: callback_query.data in ["start_requesting", "list_domains"]
)
async def handle_sending_requests(callback_query: CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    user_status = get_user_status_db(user_id)
    
    if callback_query.data == "start_requesting":
        await callback_query.message.edit_text("Ви обрали: Запустити відправку заявок")
        if user_status == EUserStatus.DEMO and active_sessions.get(user_id, []):
            await callback_query.message.answer(
                "❌ В демо статусі доступна можливість запускати одночасно лише одну сесію."
            )
        elif (
            user_status != EUserStatus.ADMIN #додав за 3 тікетом . було user_status == EUserStatus.DEMO
            and len(active_sessions.get(user_id, [])) > 2
        ):
            await callback_query.message.answer(
                "❌ Ви можете запускати лише три сесії одночасно."
            )
        else:
            await initiate_request(callback_query.message, state, user_id)
    elif callback_query.data == "list_domains":
        await callback_query.message.edit_text("Ви обрали: Активні сесії")
        await activate_requesting(callback_query.message, user_id)


# Функція перегляду активних сесій
async def activate_requesting(message, user_id):
    user_active_sessions = active_sessions.get(user_id, [])

    if not user_active_sessions:
        await message.answer("У вас поки немає активних сесій.")
    else:
        buttons = [
            [
                InlineKeyboardButton(
                    text=user_active_sessions[id], callback_data=f"remove_session_{id}"
                )
            ]
            for id in range(len(user_active_sessions))
        ]
        await message.answer(
            "Натисніть на сесію, яку хочете зупинити:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        )


# Обробник натискання інлайн кнопки "Зупинити сесію"
@request_router.callback_query(
    lambda callback_query: callback_query.data.startswith("remove_session_")
)
async def handle_remove_session(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    try:
        session_id = int(callback_query.data.split("_")[-1])
        print(active_sessions)
        session = active_sessions[user_id][session_id]
        active_sessions[user_id].remove(session)
        
        task = active_tasks[user_id].pop(session)
        task.cancel()
        # Додавання кількості запитів до кількості відправлених заявок
        count_requests = user_request_counter[user_id].pop(session)
        
        update_applications(user_id, count_requests)
        
        # users[user_id]["applications_sent"] += count_requests
        # save_users(users)
        
        await callback_query.message.edit_text(
            f"Сесія {session} зупинена успішно.\nЗаявок відправлено: {count_requests}"
        )
        await activate_requesting(callback_query.message, user_id)
    except ValueError as e:
        await callback_query.message.edit_text("Невідома сесія.")
        return await callback_query.message.answer("Не вдалось розпізнати сесію.")


# Обробник кнопки "Запустити відправку заявок"
@request_router.message(
    lambda message: (UserState.waiting_for_start or UserState.main_menu)
    and message.text == "🚀 Запустити відправку заявок"
)
async def initiate_request(message: Message, state: FSMContext, user_id=None):
    user_id = user_id or message.from_user.id
    
    logger.info(f"Користувач {user_id} натиснув кнопку 'Запустити відправку заявок'")

    # user_data = users.get(user_id, {})
    # applications_sent = user_data.get("applications_sent", 0)
    applications_sent = load_users_data_db(user_id, 'applications_sent')
    user_status = get_user_status_db(user_id)
    
    # Перевірка ліміту лише для статусу demo
    if user_status == EUserStatus.DEMO and is_demo_limit_reached(user_id):
        await message.answer(
            "❌ Ви вже досягли ліміту в 50 заявок. Для отримання повного доступу зверніться до адміністратора."
        )
        return

    # Визначити скільки заявок потрібно відправити
    if user_status == EUserStatus.DEMO:
        requests_to_send = 50 - applications_sent
        if requests_to_send <= 0:
            await message.answer(
                "❌ Ви вже досягли ліміту в 50 заявок. Для отримання повного доступу зверніться до адміністратора."
            )
            return
        await message.answer(
            f"🌐 Ви можете надіслати ще до {requests_to_send} заявок. Введіть посилання на сайт:"
        )
    else:
        await message.answer("🌐 Введіть посилання на сайт:")

    await state.set_state(UserState.waiting_for_url)


# Обробник повторного введення посилання на сайт
@request_router.message(UserState.waiting_for_url)
async def handle_url(message: Message, state: FSMContext):
    url = message.text
    user_id = message.from_user.id
    # Реалізуйте цю функцію для отримання домену з URL
    domain = extract_domain(url)
    
    # Перевірка, чи існує домен у вайтлісті інших користувачів
    # for data in users.values():
    #     print(domain)
    #     if "whitelist" in data and domain in data["whitelist"]:
    #         return await message.answer(
    #             f"❌ Домен '{domain}' вже існує у вайтлісті іншого користувача. Будь ласка, введіть інший домен."
    #         )
    if exist_domain(domain):
        return await message.answer(
                f"❌ Домен '{domain}' вже існує у вайтлісті іншого користувача. Будь ласка, введіть інший домен."
            )
    #         return await message.answer(
    #             f"❌ Домен '{domain}' вже існує у вайтлісті іншого користувача. Будь ласка, введіть інший домен."
    #         )

    # Перевірка валідності URL
    if is_valid_url(url):
        user_urls[user_id] = url
        user_active_sessions = active_sessions.get(user_id, [])
        if url in user_active_sessions:
            return await message.answer(
                f"❌ Домен '{domain}' вже існує у активних сесіях. Будь ласка, введіть інший домен."
            )
        active_sessions[user_id] = user_active_sessions + [url]
        await state.set_state(UserState.waiting_for_frequency)
        await message.answer(
            "🕰 Як швидко будуть відправлятися заявки?", reply_markup=frequency_keyboard
        )
    else:
        await message.answer("⚠️ Будь ласка, введіть коректне посилання на сайт")


# Обробник вибору тривалості
@request_router.message(
    lambda message: (
        message.text in frequency_options or message.text in duration_options
    )
    and (UserState.waiting_for_frequency or UserState.waiting_for_duration)
)
async def handle_frequency_and_duration(message: Message, state: FSMContext):
    user_id = message.from_user.id
    # user_data = users.get(user_id, {})
    
    if user_id not in active_tasks:
        active_tasks[user_id] = {}

    # Обробка вибору частоти
    state_name = await state.get_state()
    if state_name == UserState.waiting_for_frequency:
        frequency = message.text
        user_frequencies[user_id] = frequency

        # Якщо статус "demo", обираємо частоту, ігноруємо тривалість
        if get_user_status_db(user_id) == EUserStatus.DEMO:
            active_sending[user_id] = True
            await message.answer(
                "💫 Частота обрана. Вибір тривалості відправки заявок у демо статусі недоступний."
            )
            website_url = user_urls[user_id]
            await message.answer(
                f"🚀 Космічний шатл з купою заявок вже летить на сайт: {website_url}",
                reply_markup=stop_keyboard,
            )

            await task_manager.update_user_context(
                user_id, frequency, website_url, state, message
            )
            # Демо: тривалість None (без обмежень)
            active_tasks[user_id][website_url] = asyncio.create_task(
                request_loop(user_id, frequency, website_url, state, message)
            )
            return

        # Для інших статусів
        await state.set_state(UserState.waiting_for_duration)
        await message.answer(
            "⏳ Як довго будуть відправлятися заявки?",
            reply_markup=get_duration_keyboard_db(user_id),
        )
        return

    # Обробка вибору тривалості
    if state_name == UserState.waiting_for_duration:
        # Пропускаємо демо-статус для тривалості
        if get_user_status_db(user_id) != EUserStatus.DEMO:
            user_durations[user_id] = DURATION_MAPPING[message.text]

        # Підготовка до запуску відправки заявок
        frequency = user_frequencies[user_id]
        active_sending[user_id] = True
        website_url = user_urls[user_id]
        await task_manager.update_user_context(
            user_id,
            frequency,
            website_url,
            state,
            message,
            DURATION_MAPPING.get(message.text, None),
        )
        # Запуск request_loop з вказаною тривалістю
        active_tasks[user_id][website_url] = asyncio.create_task(
            request_loop(
                user_id,
                frequency,
                website_url,
                state,
                message,
                DURATION_MAPPING.get(message.text, None),
            )
        )
        await message.answer(
            f"🚀 Космічний шатл з купою заявок вже летить на сайт: {website_url}",
            reply_markup=stop_keyboard,
        )
        await state.clear()


async def request_loop(user_id, frequency, url, state, message, duration=None):
    if user_id in user_request_counter:
        user_request_counter[user_id][url] = 0  # Скинути лічильник
    else:
        user_request_counter[user_id] = {url: 0}

    delay = DELAY_MAPPING.get(frequency, 0)
    # user_data = users[user_id]

    # Якщо статус demo, кількість заявок для відправки обмежується
    requests_to_send = (
        50 - load_users_data_db(user_id, 'applications_sent')
        if get_user_status_db(user_id) == EUserStatus.DEMO
        else float("inf")
    )
    # Обчислити час закінчення, якщо тривалість обмежена
    end_time = None
    if duration is not None:
        end_time = time.time() + duration

    # proxy_index = 0
    while active_sending.get(user_id) and requests_to_send > 0:
        # Перевірка на обмеження за часом
        if end_time is not None and time.time() >= end_time:
            break
        # proxies = await get_works_proxies()
        error_message = await send_request_to_form(url, user_id)
        if error_message:
            await message.answer(
                f"❌ {error_message}\n\nЗаявок відправлено: {user_request_counter[user_id][url]}."
            )
            await task_manager.remove_user_task(
                user_id, url
            )  # Видалення задачi з контексту
            await message.answer(
                "⬇️ Використовуйте кнопку нижче:",
                reply_markup=get_start_keyboard_db(user_id),
            )  #  виправлено
            break

        if get_user_status_db(user_id) == EUserStatus.DEMO:
            requests_to_send -= 1

        logger.info(f"Затримка перед наступним запитом: {delay} секунд.")
        await asyncio.sleep(delay)

    # Оновити загальний лічильник
    request_counter = user_request_counter[user_id][url]

    await task_manager.remove_user_task(user_id, url)  # Видалення задачi з контексту

    if active_sending.get(user_id):
        await message.answer(
            f"✅ Відправка заявок на {url} завершена\n✉️ Всього відправлено заявок: {request_counter}",
            reply_markup=get_start_keyboard_db(
                user_id
            ),  # get_start_keyboard(user_id) Виправлено
        )

    active_sessions[user_id].remove(url)
    active_tasks[user_id].pop(url)
    await state.set_state(UserState.waiting_for_start)
    
    update_applications(user_id, request_counter)
    
    # users[user_id]["applications_sent"] += request_counter
    # save_users(users)  # Зберегти оновлення


# Обробник зупинки
@request_router.message(
    lambda message: active_sending.get(message.from_user.id)
    and message.text == "❌ Зупинити відправку"
)
async def stop_sending(message: Message, state: FSMContext):
    user_id = message.from_user.id
    await state.set_state(UserState.waiting_for_start)
    active_sending[user_id] = False
    for task in active_tasks.get(user_id, {}).values():
        task.cancel()
    active_tasks.pop(user_id, None)
    active_sessions.pop(user_id, None)
    total_requests = 0
    for count_requests in user_request_counter.get(user_id, {}).values():
        total_requests += count_requests
    user_request_counter.pop(user_id, None)

    # Оновлення загальної кількості заявок у users.json
    if user_in_db(user_id):
        
        update_applications(user_id, total_requests)
        # users[user_id]["applications_sent"] += total_requests
        # save_users(users)

    await message.answer(
        f"⭕️ Відправка заявок зупинена\n✉️ Всього відправлено заявок: {total_requests}",
        reply_markup=get_start_keyboard_db(user_id),
    )
