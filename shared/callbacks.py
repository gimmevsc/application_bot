from aiogram.filters.callback_data import CallbackData


class ProxyEditingCallbackData(CallbackData, prefix="prx"):

    action: str
    proxy_id: str
