"""States
FSMContext States used by the bot"""

from aiogram.fsm.state import StatesGroup, State


class Stopping(StatesGroup):
    areyousure = State()


class Searching(StatesGroup):
    option = State()


class SelectingDelete(StatesGroup):
    option = State()


class DeletingSelf(StatesGroup):
    areyousure = State()
