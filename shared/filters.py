from aiogram.filters import BaseFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message


class MultipleStateFilter(BaseFilter):
    def __init__(self, *states):
        self.states = states

    async def __call__(self, message: Message, state: FSMContext) -> bool:
        current_state = await state.get_state()
        return current_state in self.states
