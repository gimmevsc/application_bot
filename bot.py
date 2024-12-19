from contextlib import asynccontextmanager
from aiogram import Bot, Dispatcher
from fastapi import FastAPI
from routers.command_router import commands_router
from routers.admin_router import admin_router
from routers.white_list_router import white_list_router
from routers.request_router import request_router
from shared.config import API_TOKEN, WEBHOOK_URL
from shared.task_manager import TaskManager


bot = Bot(token=API_TOKEN)
dp = Dispatcher()
task_manager = TaskManager()

dp.include_routers(commands_router, admin_router, white_list_router, request_router)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await task_manager.start_listener()
    await bot.set_webhook(
        url=WEBHOOK_URL,
        allowed_updates=dp.resolve_used_update_types(),
        drop_pending_updates=True,
    )
    yield
    await bot.delete_webhook()


async def polling():
    await task_manager.start_listener()
    await dp.start_polling(bot)
