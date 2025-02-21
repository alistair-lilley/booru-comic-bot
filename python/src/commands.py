"""Commands
Registers commands via decorator
ONLY for registering commands and such
"""

from __future__ import annotations

import logging

from dotenv import dotenv_values

from aiogram import Bot, Router, Dispatcher
from aiogram import F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message
from aiogram.types.error_event import ErrorEvent
from aiogram import types
from aiogram.fsm.state import State

from boorubot import BooruComicBot
from booru_interface import BooruInterface
from comic_database import ComicDB
from comic_tracker import ComicTracker
from request_manager import RequestManager
from states import *

LOGGER = logging.getLogger(__file__)

config = dotenv_values(".env")

DEBUGGING = True if config["DEBUGGING"].lower() == "true" else False
TOKEN = config["TOKEN"]
MEEEEEEEE = config["ME"]

tgbot = Bot(TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
router = Router()
dispatcher = Dispatcher()
dispatcher.include_router(router)

reqmgr = RequestManager()
booruinterf = BooruInterface(reqmgr)
database = ComicDB("data/comicdb.json")
tracker = ComicTracker(database)
comicbot = BooruComicBot(tracker, booruinterf)


if not DEBUGGING:

    @router.error(F.update.message.as_("message"))
    async def error(event: ErrorEvent, message: Message) -> None:
        """Catches all errors"""
        LOGGER.critical("An error occurred from this message: %s", message.text)
        LOGGER.critical("error was this: %s", str(event.exception))


@router.message(F.text.startswith("/start"))
async def start(message: types.Message) -> None:
    LOGGER.info(
        "User %s (%d) started me",
        message.from_user.username,
        message.from_user.id,
    )
    await comicbot.start(message)


@router.message(F.text.startswith("/stop"))
async def stop(message: types.Message, state: State) -> None:
    """Run stop"""
    await comicbot.stop(message, state)


@router.message(DeletingSelf.areyousure, F.text == "Yes, I am absolutely sure.")
async def stop_and_delete(message: types.Message, state: State) -> None:
    """Fully stop and delete"""
    await comicbot.stop_and_delete(message, state)


@router.message(DeletingSelf.areyousure, F.text != "Yes, I am absolutely sure.")
async def dont_stop_dont_delete(message: types.Message, state: State) -> None:
    """Cancel deletion"""
    await comicbot.dont_stop_dont_delete(message, state)


@router.message(SelectingDelete.option, F.text == "cancel")
@router.message(Searching.option, F.text == "cancel")
async def cancel(message: types.Message, state: State) -> None:
    """Cancel selection"""
    LOGGER.info(
        "User %s (%d) cancelled searching or deleting",
        message.from_user.username,
        message.from_user.id,
    )
    await comicbot.cancel(message, state)


@router.message(F.text.startswith("/search"))
async def search_comic(message: types.Message, state: State) -> None:
    """Catch a search query"""
    LOGGER.info(
        "User %s (%d) searched for search query '%s'",
        message.from_user.username,
        message.from_user.id,
        message.text.split(" ", 1)[1],
    )
    await comicbot.search_comic(message, state)


@router.message(Searching.option, F.text != "cancel")
async def select_search_add_comic(message: types.Message, state: State) -> None:
    """Add to watch list"""
    LOGGER.info(
        "User %s (%d) added comic '%s' to their watchlist",
        message.from_user.username,
        message.from_user.id,
        message.text,
    )
    await comicbot.select_search_add_comic(message, state)


@router.message(F.text.startswith("/rem"))
async def select_remove_comic(message: types.Message, state: State) -> None:
    """Start removal"""
    LOGGER.info(
        "User %s (%d) is removing a comic from their list",
        message.from_user.username,
        message.from_user.id,
    )
    await comicbot.select_remove_comic(message, state)


@router.message(SelectingDelete.option, F.text != "cancel")
async def remove_comic(message: types.Message, state: State) -> None:
    """Remove from watchlist"""
    LOGGER.info(
        "User %s (%d) removed comic '%s' from their list",
        message.from_user.username,
        message.from_user.id,
        message.text,
    )
    await comicbot.remove_comic(message, state)


@router.message(F.text.startswith("/list"))
async def list_comics(message: types.Message) -> None:
    """List all user comics"""
    LOGGER.info(
        "User %s (%d) requesting their comic list",
        message.from_user.username,
        message.from_user.id,
    )
    await comicbot.list_comics(message)


@router.message(F.text.startswith("/help"))
async def send_help(message: types.Message) -> None:
    """Send help message"""
    await comicbot.send_help(message)


@router.message()
async def catchall(message: Message) -> None:
    """Catches all other messages for the pre-command checks"""
    LOGGER.info("Ignored message (%s)", message.text)
