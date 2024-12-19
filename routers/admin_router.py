from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, CallbackQuery

from shared.callbacks import ProxyEditingCallbackData
from shared.enums import EUserStatus
from shared.task_manager import TaskManager
from .command_router import UserState
from shared.funcs import (
    # get_user_status,
    get_user_status_db,
    # get_start_keyboard,
    get_start_keyboard_db,
    update_user,
    user_in_db,
    save_users,
    users,
    is_valid_proxy,
    is_proxy_working,
    toggle_proxy_state,
    generate_proxy_message,
    load_proxies,
    prepare_proxy_messages,
    update_proxy_data,
    generate_proxy_inline_keyboard,
    delete_proxy_data,
    delete_proxy,
    insert_proxy_data,
)
from shared.config import user_state
from shared.data import status_translation

admin_router = Router()
task_manager = TaskManager()


# Обробник введення Telegram ID для зміни статусу
@admin_router.message(UserState.waiting_for_user_id)
async def handle_user_id_input(message: Message, state: FSMContext):
    user_id = message.from_user.id
    target_user_id = message.text.strip()
    # user_status = get_user_status(user_id)
    user_status = get_user_status_db(user_id)
    print(target_user_id)
    print(user_in_db(target_user_id))
    
    if target_user_id.isdigit() and user_in_db(target_user_id):
        await state.set_state(UserState.waiting_for_new_status)
        user_state["target_user_id"] = int(target_user_id)
        await message.answer(
            f"🚦 Виберіть новий статус для користувача:",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text=EUserStatus.DEMO)],
                    [KeyboardButton(text=EUserStatus.UNLIMITED)],
                    [KeyboardButton(text=EUserStatus.ADMIN)],
                    [KeyboardButton(text=EUserStatus.MAX)]
                ],
                resize_keyboard=True,
                one_time_keyboard=True,
            ),
        )
    else:
        await message.answer(
            "⚠️ Некоректний ID або користувач не знайдений. Введіть правильний Telegram ID."
        )


# Обробник вибору нового статусу для користувача
@admin_router.message(UserState.waiting_for_new_status)
async def handle_new_status_selection(message: Message, state: FSMContext):
    admin_id = message.from_user.id
    new_status = message.text.strip()
    target_user_id = user_state.get("target_user_id")

    if new_status in [EUserStatus.DEMO, EUserStatus.UNLIMITED, EUserStatus.ADMIN, EUserStatus.MAX]:
        update_user(target_user_id, 'status', new_status)
        # users[target_user_id]["status"] = new_status
        # save_users(users)  # Зберігаємо зміни
        await message.answer(
            f"✅ Статус користувача з ID {target_user_id} змінено на {status_translation.get(new_status, new_status)}.",
            reply_markup=get_start_keyboard_db(admin_id),
        )
        await state.set_state(UserState.waiting_for_start)
    else:
        await message.answer(
            "⚠️ Некоректний статус. Будь ласка, виберіть із запропонованих варіантів."
        )


# Обробник створення нового проксі
@admin_router.message(lambda message: message.text == "Додати проксі")
async def handle_proxy_insert(message: Message, state: FSMContext):
    await state.set_state(UserState.waiting_for_proxy)
    await state.update_data(proxy_id=None)

    await message.answer("🌐 Введіть данні проксі у форматі IP,PORT,USERNAME,PASSWORD:")


# Обробник перемикача статусу проксі
@admin_router.callback_query(ProxyEditingCallbackData.filter(F.action == "toggle"))
async def handle_proxy_toggle_selection(
    callback_query: CallbackQuery, callback_data: ProxyEditingCallbackData
):
    proxy_id = callback_data.proxy_id
    toggle_proxy_state(proxy_id)
    await task_manager.trigger_proxy_update()

    await send_proxy_info_message(callback_query.message, proxy_id, edit=True)
    await callback_query.answer()


# Обробник введення проксі
@admin_router.callback_query(ProxyEditingCallbackData.filter(F.action == "edit"))
async def handle_proxy_input(
    callback_query: CallbackQuery,
    callback_data: ProxyEditingCallbackData,
    state: FSMContext,
):
    await state.set_state(UserState.waiting_for_proxy)
    await state.update_data(proxy_id=callback_data.proxy_id)

    await callback_query.message.edit_text(
        "🌐 Введіть данні проксі у форматі IP,PORT,USERNAME,PASSWORD:"
    )


# Обробник зміни проксі
@admin_router.message(UserState.waiting_for_proxy)
async def handle_new_proxy_selection(message: Message, state: FSMContext):
    proxy_data = message.text

    # Перевірка валідності Proxy
    if is_valid_proxy(proxy_data):
        data = await state.get_data()
        proxy_id = data.get("proxy_id")
        ip, port, login, password = proxy_data.split(",")

        if await is_proxy_working(ip, port, login, password):
            if proxy_id is None:
                update_message = "створені"
                proxy_id = insert_proxy_data(ip, port, login, password)
            else:
                update_message = "оновлені"
                update_proxy_data(proxy_id, ip, port, login, password)

            await task_manager.trigger_proxy_update()

            await send_proxy_info_message(
                message, proxy_id, update_message=update_message
            )
        else:
            await message.answer("❌ Проксі не працюють, перевірте введені дані.")
    else:
        await message.answer(
            "⚠️ Будь ласка, введіть коректне проксі у форматі IP,PORT,USERNAME,PASSWORD:"
        )


# Обробник видалення проксі
@admin_router.callback_query(ProxyEditingCallbackData.filter(F.action == "delete_data"))
async def handle_proxy_delete_data(
    callback_query: CallbackQuery, callback_data: ProxyEditingCallbackData
):
    proxy_id = callback_data.proxy_id

    delete_proxy_data(proxy_id)
    await task_manager.trigger_proxy_update()

    await send_proxy_info_message(
        callback_query.message, proxy_id, update_message="видалені", edit=True
    )


@admin_router.callback_query(
    ProxyEditingCallbackData.filter(F.action == "delete_proxy")
)
async def handle_proxy_delete_proxy(
    callback_query: CallbackQuery, callback_data: ProxyEditingCallbackData
):
    proxy_id = callback_data.proxy_id

    delete_proxy(proxy_id)
    await task_manager.trigger_proxy_update()

    await callback_query.message.delete()


# Функція для надсилання інформації про проксі у повідомленні.
async def send_proxy_info_message(message, proxy_id, update_message=None, edit=False):
    proxies = load_proxies()
    proxy_data = proxies.get(proxy_id)

    toggle_message = (
        f"Проксі {proxy_id} успiшно {update_message}.\n\n" if update_message else ""
    )
    proxy_info_message = generate_proxy_message(proxy_id, proxy_data)
    full_message = toggle_message + proxy_info_message

    keyboard = generate_proxy_inline_keyboard(proxy_id, proxy_data["use_proxy"])

    if edit:
        await message.edit_text(full_message, reply_markup=keyboard)
    else:
        await message.answer(full_message, reply_markup=keyboard)
