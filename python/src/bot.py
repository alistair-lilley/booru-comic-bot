"""BooruComicBot
The BooruComicBot proper
This file is to contain all the main logic of the BooruComicBot, but not registering any events or anything
"""

from __future__ import annotations

import re
import asyncio
import logging

from typing import TYPE_CHECKING, Dict

from aiogram import types, Bot
from aiogram.enums import ParseMode
from aiogram.fsm.state import State
from aiogram.types.keyboard_button import KeyboardButton
from aiogram.types.reply_keyboard_markup import ReplyKeyboardMarkup
from aiogram.types.reply_keyboard_remove import ReplyKeyboardRemove

from states import *

if TYPE_CHECKING:
    from booru_interface import booru_interface
    from comic_tracker import ComicTracker
    from comic_database import ComicObj

LOGGER = logging.getLogger(__file__)


class BooruComicBot:
    """Contains all the logic for this BooruComicBot"""

    def __init__(
        self: BooruComicBot, comic_tracker: ComicTracker, booru_interface: booru_interface
    ):
        self._comic_tracker = comic_tracker
        self._booru_interface = booru_interface

    async def start(self: BooruComicBot, message: types.Message) -> None:
        """Send initialization message"""
        await message.answer("Welcome to BooruComicBooruComicBot!")

    async def stop(self: BooruComicBot, message: types.Message, state: State) -> None:
        """Start the process of deleting user from database; send 'are you sure' message"""
        await state.set_state(DeletingSelf.areyousure)
        await message.answer(
            "Are you sure you want to stop this BooruComicBot? You will be deleted from the system, "
            "losing all of your comics and no longer getting updates.\nIf you're sure, type in the "
            "following, excatly:\n<b>Yes, I am absolutely sure.</b>",
            parse_mode=ParseMode.HTML,
        )

    async def stop_and_delete(
        self: BooruComicBot, message: types.Message, state: State
    ) -> None:
        """Remove all instances of user from database"""
        await message.answer("Deleting you from my system. Goodbye!")
        userid = str(message.from_user.id)
        self._comic_tracker.remove_from_all(userid)
        await state.clear()

    async def dont_stop_dont_delete(
        self: BooruComicBot, message: types.Message, state: State
    ) -> None:
        """Clear state and send 'not deleting' message"""
        await message.answer("Whew! Not deleted!")
        await state.clear()

    async def cancel(self: BooruComicBot, message: types.Message, state: State) -> None:
        """Cancel one of multiple commands"""
        await message.answer("Cancelling", reply_markup=ReplyKeyboardRemove())
        await state.clear()

    async def search_comic(
        self: BooruComicBot, message: types.Message, state: State
    ) -> None:
        """Take a search query and retrieve comic option results from booru sites,
        then present those options
        """
        if " " not in message.text:
            await message.answer("Enter a search query after '/search'!")

        rawquery = message.text.strip().split(" ", 1)[1]
        search_results = await self._booru_interface.fetch_search(rawquery)
        options = self._booru_interface._format_options(search_results)

        if len(options) == 0:
            await message.answer("No search results found!")
            return

        keyboardbuttons = [
            [KeyboardButton(text=opt) for opt in options[n : n + 2]]
            for n in range(0, len(options), 2)
        ]
        keyboardbuttons.append([KeyboardButton(text="cancel")])
        keyboard = ReplyKeyboardMarkup(keyboard=keyboardbuttons)

        await message.answer("Pick from the following comics", reply_markup=keyboard)
        await state.set_state(Searching.option)

    async def select_search_add_comic(
        self: BooruComicBot, message: types.Message, state: State
    ) -> None:
        """Select from the options given by search_comic, add comic to db and update"""
        user_id = str(message.from_user.id)
        comic_id = re.findall("\([\d]+\)", message.text)[-1].strip("()")
        isnewcomic = self._comic_tracker.add_user_to_comic(user_id, comic_id)

        if isnewcomic:
            comic_data = await self._booru_interface.fetch_pool(comic_id)
            self._comic_tracker.update_comic(comic_id, comic_data)

        await message.answer("Comic added!", reply_markup=ReplyKeyboardRemove())
        await state.clear()

    async def select_remove_comic(
        self: BooruComicBot, message: types.Message, state: State
    ) -> None:
        """List all comics the user is following for selection for removal"""
        user_id = str(message.from_user.id)
        comics = self._comic_tracker.fetch_users_comics(user_id)
        options = self._booru_interface._format_options(comics)

        if len(options) == 0:
            await message.answer("You're not following any comics")
            return

        keyboardoptions = [
            [KeyboardButton(text=opt) for opt in options[n : n + 2]]
            for n in range(0, len(options), 2)
        ]
        keyboardoptions.append([KeyboardButton(text="cancel")])
        keyboard = ReplyKeyboardMarkup(keyboard=keyboardoptions)

        await message.answer("Pick a comic to remove", reply_markup=keyboard)
        await state.set_state(SelectingDelete.option)

    async def remove_comic(
        self: BooruComicBot, message: types.Message, state: State
    ) -> None:
        """Remove user from selected comic in the database"""
        user_id = str(message.from_user.id)
        comic_id = re.findall("\([\d]+\)", message.text)[-1].strip("()")
        self._comic_tracker.remove_user_from_comic(user_id, comic_id)

        await message.answer("Comic removed!", reply_markup=ReplyKeyboardRemove())
        await state.clear()

    async def list_comics(self: BooruComicBot, message: types.Message) -> None:
        """List all comics a user is following"""
        user_id = str(message.from_user.id)
        comiclist = self._comic_tracker.fetch_users_comics(user_id)

        if not comiclist:
            await message.answer("You're not following any comics!")
            return

        await message.answer(
            "You're following these comics:\n" + "\n".join(comiclist),
        )

    async def send_help(self: BooruComicBot, message: types.Message) -> None:
        """Send help message with all commands"""
        await message.answer(
            "Hi! Welcome to the Booru Comic Watch BooruComicBot!\nI'm a nifty little BooruComicBot that can help you "
            "keep track of comics you'd like to follow that are posted on a booru site!\nHere's a summary "
            "of my commands:\n/start - Start me up and set up a watch list!\n/stop - Delete "
            "yourself from this BooruComicBot! *WARNING: You'll lose all of your watched comics!*\n/help "
            "- Show this message!\n/search - [name] - Search a comic by name! I'll give you a list "
            "of options to choose from!\n/rem - Remove a comic from your watch list! I'll give you "
            "a list of options to chosoe from!\n/list - List all of the comics you're watching "
            "(including their ID numbers)! This will link them too!\nNote that I'm still being "
            "tweaked, so changes may happen! If anything major changes, I'll tell you!\nEnjoy!",
        )

    async def _send_all_updates(
        self: BooruComicBot, tgBooruComicBot: Bot, updates: Dict
    ) -> None:
        for comic_id, comicupdates in updates.values():
            pages = comicupdates["pages"]
            users = comicupdates["users"]

            for page in pages:
                LOGGER.info(
                    "Sending page %s of comic %s to users %s", page, comic_id, users
                )
                for user in users:
                    await tgBooruComicBot.send_message(user, page)

    async def loop_send_updates(self: BooruComicBot, tgBooruComicBot: Bot) -> None:
        """Loop over comics in database and send updates when updates found"""
        while True:
            curr_comics: Dict[int, ComicObj] = self._comic_tracker.comics
            updates, full_updates = await self._booru_interface.check_fetch_updates(curr_comics)

            if updates:
                await self._send_all_updates(tgBooruComicBot, updates)
                for comic_id, comic_updates in full_updates.items():
                    self._comic_tracker.update_comic(comic_id, comic_updates)

            else:
                LOGGER.info("No updates found, waiting %s seconds", 60)
                await asyncio.sleep(60)
