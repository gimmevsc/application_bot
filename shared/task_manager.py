import asyncio

from shared.config import active_tasks, user_request_counter, logger


class TaskManager:
    _instance = None
    _listener_task = None
    _proxy_update_event: asyncio.Event = asyncio.Event()
    _user_context: dict = {}  # Контекст користувачів з інформацією про запити

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(TaskManager, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    #  Функція для запуску слухача змін проксі, якщо він ще не запущений.
    async def start_listener(self):
        if self._listener_task is None:
            self._listener_task = asyncio.create_task(self.proxy_change_listener())

    # Функція для ініціації оновлення проксі, яка сигналізує слухачеві про необхідність обробки змін.
    async def trigger_proxy_update(self):
        self._proxy_update_event.set()

    #  Функція для слухання змін проксі та перезапуску запитів для користувачів з збереженням лічильників.
    async def proxy_change_listener(self):
        while True:
            await self._proxy_update_event.wait()

            for user_id, tasks in self._user_context.items():
                counters = await self.stop_active_tasks_with_counters(user_id)

                for website_url, task_data in tasks.items():

                    frequency = task_data["frequency"]
                    state = task_data["state"]
                    message = task_data["message"]
                    duration = task_data["duration"]

                    await self.restart_user_requests_with_counters(
                        user_id, frequency, counters, state, message, duration
                    )

            self._proxy_update_event.clear()

    #  Функція для зупинки активних задач для вказаного користувача та збереження лічильників відправлених запитів.
    async def stop_active_tasks_with_counters(self, user_id):
        counters = {}
        if user_id in active_tasks:
            for url, task in active_tasks[user_id].items():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    logger.info(
                        f"Завдання для користувача {user_id} та URL {url} зупинено."
                    )

                counters[url] = user_request_counter[user_id].get(url, 0)

            active_tasks[user_id].clear()

        return counters

    # Функція для запуску нових задач для відправки запитів зі збереженням лічильників.
    async def restart_user_requests_with_counters(
        self, user_id, frequency, counters, state, message, duration
    ):

        from routers.request_router import request_loop

        website_urls = user_request_counter[user_id].keys()

        for url in website_urls:
            user_request_counter[user_id][url] = counters.get(url, 0)

            active_tasks[user_id][url] = asyncio.create_task(
                request_loop(user_id, frequency, url, state, message, duration=duration)
            )

    # Функція для оновлення контексту користувача або створення нового, якщо ще не існує
    async def update_user_context(
        self, user_id, frequency, website_url, state, message, duration=None
    ):

        if user_id not in self._user_context:
            self._user_context[user_id] = {}

        self._user_context[user_id][website_url] = {
            "frequency": frequency,
            "state": state,
            "message": message,
            "duration": duration,
        }

    # Функція для видалення завдання користувача для певного URL з контексту
    async def remove_user_task(self, user_id, url):

        if user_id in self._user_context and url in self._user_context[user_id]:
            del self._user_context[user_id][url]
            logger.info(
                f"Контекст користувача {user_id} для URL {url} видалено з user_context."
            )

        if user_id in self._user_context and not self._user_context[user_id]:
            del self._user_context[user_id]
            logger.info(f"Контекст користувача {user_id} повністю очищений.")
